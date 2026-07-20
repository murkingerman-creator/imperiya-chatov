import random
import secrets
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from bot import config
from db.models import Player
from services.player import ensure_aware, regenerate_energy, utcnow


class WorkError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


@dataclass
class MiniSession:
    vk_id: int
    job: str
    token: str
    correct: str
    expires_at: float
    meta: dict


_sessions: dict[str, MiniSession] = {}


def _job_last_attr(job: str) -> str:
    mapping = {
        "mine": "last_mine_at",
        "market": "last_market_at",
        "guard": "last_guard_at",
        "fish": "last_fish_at",
        "farm": "last_farm_at",
        "forge": "last_forge_at",
        "tavern": "last_tavern_at",
        "stable": "last_stable_at",
    }
    if job not in mapping:
        raise WorkError("Неизвестная работа.")
    return mapping[job]


def check_can_start_job(player: Player, job: str, *, skip_cd: bool = False) -> dict:
    if job not in config.JOBS:
        raise WorkError("Неизвестная работа.")
    from services.levels import job_unlocked

    if not job_unlocked(player, job):
        req = config.JOB_LEVEL_REQ.get(job, 1)
        raise WorkError(
            f"{config.JOBS[job]['title']} откроется с {req} уровня "
            f"(у тебя {int(player.level or 1)})."
        )
    regenerate_energy(player)
    until = ensure_aware(player.jail_until)
    if until and utcnow() < until:
        left = int((until - utcnow()).total_seconds() / 60) + 1
        raise WorkError(
            f"Ты в тюрьме ещё ~{left} мин. Выкуп за кроны: 🔓 / 🏪 Лавка."
        )
    spec = config.JOBS[job]
    now = utcnow()
    if not skip_cd:
        last = ensure_aware(getattr(player, _job_last_attr(job), None))
        if last:
            ready_at = last + timedelta(minutes=spec["cooldown_min"])
            if now < ready_at:
                minutes_left = int((ready_at - now).total_seconds() / 60) + 1
                raise WorkError(
                    f"{spec['title']}: кулдаун. Подожди ещё ~{minutes_left} мин."
                )
    if player.energy < 1:
        raise WorkError("Недостаточно энергии.")
    return spec


def _build_minigame(job: str) -> tuple[str, str, list[tuple[str, str]], dict]:
    """prompt, correct, buttons, meta — у каждой работы свой паттерн."""
    now = utcnow().timestamp()

    if job == "mine":
        # риск: осторожно = стабильно; глубже = джекпот или обвал
        return (
            "⛏ Шахта: жила манит вглубь.\n"
            "Осторожно — меньше, но верно.\n"
            "Глубже — ×2 или обвал.",
            "choice",
            [("🛡 Осторожно", "careful"), ("💥 Глубже!", "deep")],
            {"mode": "risk"},
        )

    if job == "market":
        buy = random.randint(25, 55)
        return (
            f"🛒 Рынок: лот за {buy} крон (оценка).\n"
            f"Покупаешь или пропускаешь?",
            "buy",  # не равенство — mode=market
            [("✅ Купить", "buy"), ("⏭ Пропустить", "skip")],
            {"mode": "market", "step": 1, "buy_price": buy},
        )

    if job == "guard":
        faces = ["🙂", "😎", "🥸", "😐"]
        random.shuffle(faces)
        spy_idx = random.randint(0, 2)
        shown = "  ".join(f"{i + 1}){faces[i]}" for i in range(3))
        return (
            f"🛡 Охрана: запомни шпиона!\n{shown}\n"
            f"Кто лишний? (смотри внимательно)",
            str(spy_idx),
            [(f"{i + 1} {faces[i]}", str(i)) for i in range(3)],
            {"mode": "memory", "faces": faces},
        )

    if job == "fish":
        delay = random.uniform(1.8, 4.5)
        bite_at = now + delay
        return (
            "🎣 Рыбалка: вода спокойна…\n"
            "Не торопись — подожди пару секунд,\n"
            "потом жми «Подсечь». Рано / поздно — мимо.",
            "hook",
            [("🎣 Подсечь", "hook")],
            {"mode": "timing", "bite_at": bite_at, "window": 10.0},
        )

    if job == "farm":
        # погода дня (стабильна в пределах часа)
        hour_seed = int(utcnow().timestamp() // 3600)
        weather = ["drought", "rain", "ripe"][hour_seed % 3]
        labels = {
            "drought": "🔥 Засуха — полей",
            "rain": "🌧 Дождь — пропали сорняки? Прополи",
            "ripe": "☀️ Всё зрело — собирай",
        }
        correct = {"drought": "water", "rain": "weed", "ripe": "harvest"}[weather]
        return (
            f"🌾 Поле сегодня: {labels[weather]}\nЧто делать?",
            correct,
            [("💧 Полить", "water"), ("🌿 Прополоть", "weed"), ("🧺 Собрать", "harvest")],
            {"mode": "weather", "weather": weather},
        )

    if job == "forge":
        steps = random.sample(["soft", "hard", "quench"], 3)
        labels = {"soft": "🔨 Легко", "hard": "⚔ Сильно", "quench": "❄ Закалить"}
        preview = " → ".join(labels[s] for s in steps)
        return (
            f"🔥 Кузня: повтори ритм!\n{preview}\n"
            f"Шаг 1/{len(steps)} — первый удар:",
            steps[0],
            [(labels[k], k) for k in ("soft", "hard", "quench")],
            {"mode": "chain", "steps": steps, "idx": 0, "labels": labels},
        )

    if job == "tavern":
        # выбор без провала — разные награды
        return (
            "🍺 Таверна: чем берёшь зал?\n"
            "Эль — стабильно · Песня — риск чаевых · Сделка — жирно/пусто",
            "choice",
            [("🍺 Эль", "ale"), ("🎵 Песня", "song"), ("🃏 Сделка", "deal")],
            {"mode": "tavern"},
        )

    if job == "stable":
        hour_seed = int(utcnow().timestamp() // 3600)
        mood = ["restless", "hungry", "dirty"][hour_seed % 3]
        labels = {
            "restless": "🐴 Конь беспокойный — нужен выгул",
            "hungry": "🐴 Конь голоден — покорми",
            "dirty": "🐴 Шерсть в грязи — вычисти",
        }
        correct = {"restless": "walk", "hungry": "feed", "dirty": "groom"}[mood]
        return (
            f"🐴 Имперская конюшня\n{labels[mood]}\nЧто сделать?",
            correct,
            [
                ("🧹 Вычистить", "groom"),
                ("🚶 Выгул", "walk"),
                ("🥕 Покормить", "feed"),
            ],
            {"mode": "stable", "mood": mood},
        )

    raise WorkError("Неизвестная работа.")


def start_minigame(
    player: Player, job: str, *, skip_cd: bool = False, charge_flags: dict | None = None
) -> dict:
    check_can_start_job(player, job, skip_cd=skip_cd)
    token = secrets.token_hex(4)
    now_ts = utcnow().timestamp()
    prompt, correct, buttons, meta = _build_minigame(job)
    meta.update(charge_flags or {})
    ttl = 90 if meta.get("mode") in ("chain", "market", "timing") else 60

    for k, s in list(_sessions.items()):
        if s.vk_id == player.vk_id or s.expires_at < now_ts:
            _sessions.pop(k, None)

    _sessions[token] = MiniSession(
        vk_id=player.vk_id,
        job=job,
        token=token,
        correct=correct,
        expires_at=now_ts + ttl,
        meta=meta,
    )
    return {"token": token, "prompt": prompt, "buttons": buttons, "job": job}


def _resolve_answer(game: MiniSession, answer: str) -> dict:
    """Разбор ответа. continue=True — ещё шаг; иначе success + множители."""
    mode = game.meta.get("mode") or "simple"
    now = utcnow().timestamp()

    if mode == "timing":
        bite = float(game.meta.get("bite_at") or 0)
        window = float(game.meta.get("window") or 7)
        if answer != "hook":
            return {"success": False, "note": "Не та кнопка."}
        if now < bite:
            return {"success": False, "note": "Рано — рыба ушла."}
        if now > bite + window:
            return {"success": False, "note": "Поздно — сорвалась."}
        return {"success": True, "note": "Есть!"}

    if mode == "risk":
        if answer == "careful":
            return {
                "success": True,
                "reward_mult": 0.85,
                "note": "Осторожная добыча.",
            }
        if answer == "deep":
            if random.random() < 0.48:
                return {
                    "success": True,
                    "reward_mult": 1.85,
                    "note": "Жила! Глубина окупилась.",
                }
            return {
                "success": False,
                "reward_mult": 0.25,
                "note": "Обвал. Еле выбрался.",
            }
        return {"success": False, "note": "Замер в штольне."}

    if mode == "tavern":
        if answer == "ale":
            return {
                "success": True,
                "reward_mult": 1.0,
                "note": "Эль и чаевые — ровно.",
            }
        if answer == "song":
            if random.random() < 0.55:
                return {
                    "success": True,
                    "reward_mult": 1.45,
                    "note": "Зал ревел — чаевые жирные.",
                }
            return {
                "success": True,
                "reward_mult": 0.7,
                "note": "Спел мимо ноты. Кинули мелочью.",
            }
        if answer == "deal":
            if random.random() < 0.4:
                return {
                    "success": True,
                    "reward_mult": 1.9,
                    "note": "Тёмная сделка — карман тяжёлый.",
                }
            return {
                "success": True,
                "reward_mult": 0.45,
                "note": "Обманули за карточным столом.",
            }
        return {"success": True, "reward_mult": 0.8, "note": "Смена как смена."}

    if mode == "chain":
        steps = list(game.meta.get("steps") or [])
        idx = int(game.meta.get("idx") or 0)
        labels = game.meta.get("labels") or {}
        if idx >= len(steps) or answer != steps[idx]:
            return {"success": False, "note": "Ритм сбит — металл остыл."}
        idx += 1
        game.meta["idx"] = idx
        if idx < len(steps):
            game.correct = steps[idx]
            nxt = labels.get(steps[idx], steps[idx])
            return {
                "continue": True,
                "prompt": (
                    f"🔥 Верно! Шаг {idx + 1}/{len(steps)} — {nxt}"
                ),
                "buttons": [
                    (labels.get(k, k), k) for k in ("soft", "hard", "quench")
                ],
            }
        return {"success": True, "note": "Клинок закалён. Ритм идеален."}

    if mode == "market":
        step = int(game.meta.get("step") or 1)
        if step == 1:
            if answer == "skip":
                return {
                    "success": True,
                    "reward_mult": 0.75,
                    "note": "Пропустил лот — мелочь с соседнего прилавка.",
                }
            if answer != "buy":
                return {"success": False, "note": "Растерялся у прилавка."}
            buy = int(game.meta.get("buy_price") or 40)
            move = random.randint(-18, 22)
            sell = max(10, buy + move)
            game.meta["step"] = 2
            game.meta["sell_price"] = sell
            game.correct = "sell"
            return {
                "continue": True,
                "prompt": (
                    f"🛒 Купил за {buy}. Курс ушёл: теперь {sell}.\n"
                    f"Продаёшь или ждёшь отскока?"
                ),
                "buttons": [("💰 Продать", "sell"), ("⏳ Ждать", "wait")],
            }
        buy = int(game.meta.get("buy_price") or 40)
        sell = int(game.meta.get("sell_price") or buy)
        if answer == "sell":
            if sell >= buy:
                return {
                    "success": True,
                    "reward_mult": 1.0 + min(0.6, (sell - buy) / max(buy, 1)),
                    "note": f"Продал с плюсом ({buy}→{sell}).",
                }
            return {
                "success": True,
                "reward_mult": 0.55,
                "note": f"Продал в минус ({buy}→{sell}).",
            }
        if answer == "wait":
            rebound = sell + random.randint(-8, 20)
            if rebound > sell:
                return {
                    "success": True,
                    "reward_mult": 1.25,
                    "note": f"Отскок! Выждал {rebound}.",
                }
            return {
                "success": True,
                "reward_mult": 0.5,
                "note": "Ждал зря — цена просела ещё.",
            }
        return {"success": False, "note": "Упустил момент."}

    # simple / memory / weather / stable
    ok = answer == game.correct
    return {
        "success": ok,
        "note": "Верно." if ok else "Мимо.",
    }


async def finish_minigame(
    session: AsyncSession, player: Player, token: str, answer: str
) -> dict:
    from services.item_effects import (
        apply_work_modifiers,
        consume_buff_stack,
        get_buff,
        get_loadout,
        set_buff,
        try_consume_charge,
    )
    from services.loot import grant_drop
    from services.quests import on_job_done
    from services.flash_events import get_flash_event
    from services.world_events import (
        get_active_event,
        loot_multiplier,
        tax_modifier,
        work_multiplier,
    )

    game = _sessions.get(token)
    if not game or game.vk_id != player.vk_id:
        _sessions.pop(token, None)
        raise WorkError("Мини-игра не найдена или устарела. Начни работу заново.")
    if utcnow().timestamp() > game.expires_at:
        _sessions.pop(token, None)
        raise WorkError("Время вышло. Попробуй работу снова.")

    resolved = _resolve_answer(game, answer)
    if resolved.get("continue"):
        # сессию оставляем
        return {
            "continue": True,
            "token": token,
            "prompt": resolved["prompt"],
            "buttons": resolved["buttons"],
            "job": game.job,
        }

    _sessions.pop(token, None)

    skip_cd = bool(game.meta.get("free_mine"))
    spec = check_can_start_job(player, game.job, skip_cd=skip_cd)
    success = bool(resolved.get("success"))
    loadout = await get_loadout(session, player)

    charge_notes: list[str] = []
    if resolved.get("note"):
        charge_notes.append(str(resolved["note"]))
    free_mine_ok = False

    # free mine charge consume
    if game.meta.get("free_mine"):
        name = await try_consume_charge(session, player, "free_mine_x2", loadout)
        if name:
            free_mine_ok = True
            charge_notes.append(f"⚡ {name}: шахта без КД ×2")
            loadout = await get_loadout(session, player)

    # activate no_tax_3 if ready and no active buff
    buff = await get_buff(session, player.vk_id, "no_tax_3")
    if (not buff or buff.stacks <= 0) and "no_tax_3" in loadout.charges_ready:
        name = await try_consume_charge(session, player, "no_tax_3", loadout)
        if name:
            await set_buff(session, player.vk_id, "no_tax_3", 3)
            charge_notes.append(f"⚡ {name}: 3 работы без налога")
            buff = await get_buff(session, player.vk_id, "no_tax_3")

    base = random.randint(spec["reward_min"], spec["reward_max"])
    if resolved.get("reward_mult") is not None:
        if success:
            mult = float(spec["success_mult"]) * float(resolved["reward_mult"])
        else:
            mult = float(spec["fail_mult"]) * float(resolved["reward_mult"])
    else:
        mult = spec["success_mult"] if success else spec["fail_mult"]

    ev = await get_active_event(session)
    flash = await get_flash_event(session)
    event_key = ev["key"] if ev else None

    # personal gold vein / ignore plague
    work_ev_mult = work_multiplier(ev, flash)
    if loadout.personal_gold_vein:
        work_ev_mult = max(work_ev_mult, 1.5)
        event_key = "gold_vein"
    if ev and ev.get("key") == "plague" and "ignore_plague" in loadout.charges_ready:
        name = await try_consume_charge(session, player, "ignore_plague", loadout)
        if name:
            work_ev_mult = work_multiplier(None, flash)
            charge_notes.append(f"⚡ {name}: чума не действует")
    if flash:
        charge_notes.append(f"⚡ {flash['title']}")

    gross = max(1, int(base * mult * work_ev_mult))
    gross, item_mult = apply_work_modifiers(gross, loadout, game.job)
    work_buff_until = (
        ensure_aware(player.nation.work_buff_until)
        if player.nation_id and player.nation
        else None
    )
    if work_buff_until and work_buff_until > utcnow():
        gross = max(1, int(gross * 1.10))
        charge_notes.append("📜 Указ о труде: +10% доход")

    from services.cataclysm import cataclysm_loot_mult, cataclysm_work_mult, get_cataclysm
    from services.continents import get_continent_buff
    from services.districts import market_work_bonus, temple_luck_bonus
    from services.empire import get_empire_status
    from services.trophies import relic_bonuses
    from services.professions import bump_job, work_bonus_for
    from content.job_flavor import pick_flavor

    prof_b = work_bonus_for(player, game.job)
    if prof_b:
        gross = max(1, int(gross * (1.0 + prof_b)))
        charge_notes.append(f"🏅 Ранг профессии: +{int(prof_b * 100)}%")

    if await consume_buff_stack(session, player.vk_id, "craft_boost"):
        craft_b = float(config.SHOP_CRAFT_LICENSE_BONUS)
        gross = max(1, int(gross * (1.0 + craft_b)))
        charge_notes.append(f"📜 Лицензия мастерства: +{int(craft_b * 100)}%")

    tribute = await get_buff(session, player.vk_id, "tribute_work")
    if tribute:
        trib_b = float(config.SHOP_TRIBUTE_WORK_BONUS)
        gross = max(1, int(gross * (1.0 + trib_b)))
        charge_notes.append(f"🕯 Подношение трону: +{int(trib_b * 100)}%")

    cata = await get_cataclysm(session)
    cata_w = cataclysm_work_mult(cata)
    if cata_w != 1.0:
        gross = max(1, int(gross * cata_w))
        charge_notes.append(f"🌪 {cata['title']}: ×{cata_w:.2f}")

    market_b = market_work_bonus(player.nation if player.nation_id else None)
    if market_b:
        gross = max(1, int(gross * (1.0 + market_b)))
        charge_notes.append(f"🛒 Рынок столицы: +{int(market_b * 100)}%")

    if player.nation and int(player.nation.monument_level or 0) > 0:
        mon = int(player.nation.monument_level) * float(config.TREASURY_MONUMENT_WORK)
        gross = max(1, int(gross * (1.0 + mon)))
        charge_notes.append(f"🗿 Монумент ур.{player.nation.monument_level}: +{int(mon*100)}%")

    relic_w, _ = relic_bonuses(player.nation if player.nation_id else None)
    if relic_w:
        gross = max(1, int(gross * (1.0 + relic_w)))
        charge_notes.append(f"🕯 Реликвия нации: +{int(relic_w * 100)}%")

    empire = await get_empire_status(session)
    if empire:
        gross = max(1, int(gross * (1.0 + float(empire["work_mult"]))))
        charge_notes.append(
            f"🏛 Указ Империи: +{int(empire['work_mult'] * 100)}%"
        )

    cbuff = await get_continent_buff(session)
    if (
        cbuff
        and player.nation
        and (player.nation.continent or "") == cbuff.get("bloc")
    ):
        gross = max(1, int(gross * (1.0 + float(cbuff["work_mult"]))))
        charge_notes.append(
            f"🗺 Бафф континента: +{int(cbuff['work_mult'] * 100)}%"
        )

    if free_mine_ok:
        gross *= 2

    if await consume_buff_stack(session, player.vk_id, "work_luck"):
        bonus = 1.0 + config.SHOP_WORK_LUCK_BONUS
        gross = max(1, int(gross * bonus))
        charge_notes.append(
            f"🍀 Печать удачи: +{int(config.SHOP_WORK_LUCK_BONUS * 100)}%"
        )

    tax = 0
    nation_name = None
    treasury_bonus = 0
    no_tax = await consume_buff_stack(session, player.vk_id, "no_tax_3")
    if no_tax:
        charge_notes.append("🏛 Налог: 0 (заряд)")

    if player.nation_id and player.nation and not no_tax:
        nation_name = player.nation.name
        tax_rate = (
            (player.nation.tax_rate or config.TAX_RATE)
            + tax_modifier(ev, flash)
            + loadout.tax_add
        )
        tax_rate = max(0.0, min(0.4, tax_rate))
        tax = max(1, int(gross * tax_rate))
        player.nation.treasury += tax
        from services.tax_week import add_tax_paid

        add_tax_paid(player, tax)
        if success and game.job == "guard":
            treasury_bonus = int(spec.get("treasury_bonus", 0)) + loadout.treasury_bonus_add
            player.nation.treasury += treasury_bonus

    net = gross - tax
    player.crowns += net
    player.energy -= 1
    now = utcnow()
    setattr(player, _job_last_attr(game.job), now)
    player.last_work_at = now
    player.energy_updated_at = now

    # full energy on successful guard
    if success and game.job == "guard" and "full_energy_guard" in loadout.charges_ready:
        name = await try_consume_charge(session, player, "full_energy_guard", loadout)
        if name:
            player.energy = config.MAX_ENERGY
            charge_notes.append(f"⚡ {name}: энергия восстановлена")

    rank_info = bump_job(player, game.job)
    if rank_info.get("note"):
        charge_notes.append(rank_info["note"])

    await session.commit()

    if player.nation_id:
        from services.weeklies import add_progress
        from services.caravan import on_nation_job

        await add_progress(session, player.nation_id, "jobs_total", 1)
        if tax:
            await add_progress(session, player.nation_id, "treasury_gain", tax)
        caravan_note = await on_nation_job(session, player)
        if caravan_note:
            charge_notes.append(caravan_note)

    quest_extra = 0
    if "quest_x2" in loadout.charges_ready:
        name = await try_consume_charge(session, player, "quest_x2", loadout)
        if name:
            quest_extra = 1
            charge_notes.append(f"⚡ {name}: квест ×2")

    quest = await on_job_done(session, player)
    if quest_extra:
        quest = await on_job_done(session, player)

    from services.contracts import on_job_for_contracts

    contract_note = await on_job_for_contracts(session, player, game.job)
    if contract_note:
        charge_notes.append(contract_note)

    from services.levels import add_xp

    xp_info = await add_xp(session, player, config.XP_JOB, reason="работа")
    if xp_info.get("level_ups"):
        charge_notes.extend(xp_info["level_ups"])
    elif xp_info.get("gained"):
        charge_notes.append(f"⭐ +{xp_info['gained']} XP")

    charge_notes.append(f"📖 {pick_flavor(game.job)}")

    drop_pool = spec.get("loot_pool") or game.job
    if cata and cata.get("loot_pool"):
        drop_pool = cata["loot_pool"]
    loot_m = loot_multiplier(ev, flash) * cataclysm_loot_mult(cata)
    luck = float(loadout.loot_luck or 0.0)
    luck += temple_luck_bonus(player.nation if player.nation_id else None)
    if empire:
        luck += float(empire["loot_luck"])
    drop = await grant_drop(
        session,
        player,
        drop_pool,
        success=success,
        job=game.job,
        event_key=event_key,
        loot_luck=luck,
        loot_mult=loot_m,
    )
    if game.job == "mine" and "double_loot_mine" in loadout.charges_ready:
        name = await try_consume_charge(session, player, "double_loot_mine", loadout)
        if name:
            drop2 = await grant_drop(
                session,
                player,
                "mine",
                success=True,
                job="mine",
                event_key=event_key,
                loot_luck=loadout.loot_luck + 0.05,
                loot_mult=loot_m,
            )
            charge_notes.append(f"⚡ {name}: двойной дроп")
            if drop2 and not drop:
                drop = drop2
            elif drop2:
                drop = {
                    **drop2,
                    "text": f"{drop['text'] if drop else ''}\n{drop2['text']}".strip(),
                }

    return {
        "success": success,
        "job": game.job,
        "title": spec["title"],
        "gross": gross,
        "tax": tax,
        "net": net,
        "crowns": player.crowns,
        "energy": player.energy,
        "nation_name": nation_name,
        "treasury_bonus": treasury_bonus,
        "correct": game.correct,
        "quest": quest,
        "drop": drop,
        "charge_notes": charge_notes,
        "item_mult": item_mult,
    }


async def do_work(session: AsyncSession, player: Player) -> dict:
    """Быстрая работа без мини-игры (совместимость / тесты)."""
    regenerate_energy(player)
    now = utcnow()
    last = ensure_aware(player.last_mine_at or player.last_work_at)
    if last:
        ready_at = last + timedelta(minutes=config.JOBS["mine"]["cooldown_min"])
        if now < ready_at:
            raise WorkError("Кулдаун шахты.")
    if player.energy < 1:
        raise WorkError("Недостаточно энергии.")

    gross = random.randint(45, 90)
    tax = 0
    nation_name = None
    if player.nation_id and player.nation:
        nation_name = player.nation.name
        rate = player.nation.tax_rate or 0.1
        tax = max(1, int(gross * rate))
        player.nation.treasury += tax
    net = gross - tax
    player.crowns += net
    player.energy -= 1
    player.last_mine_at = now
    player.last_work_at = now
    await session.commit()
    return {
        "gross": gross,
        "tax": tax,
        "net": net,
        "crowns": player.crowns,
        "energy": player.energy,
        "nation_name": nation_name,
    }
