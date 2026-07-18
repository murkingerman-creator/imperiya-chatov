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
    }
    if job not in mapping:
        raise WorkError("Неизвестная работа.")
    return mapping[job]


def check_can_start_job(player: Player, job: str, *, skip_cd: bool = False) -> dict:
    if job not in config.JOBS:
        raise WorkError("Неизвестная работа.")
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
    """prompt, correct, buttons, meta"""
    if job == "mine":
        correct = random.choice(["A", "B", "C"])
        return (
            "⛏ Шахта: в какой штольне руда?\nВыбери A / B / C.",
            correct,
            [("Штольня A", "A"), ("Штольня B", "B"), ("Штольня C", "C")],
            {},
        )
    if job == "market":
        rate = random.randint(40, 80)
        correct = random.choice(["up", "down"])
        return (
            f"🛒 Рынок: курс сейчас {rate}.\nКуда пойдёт цена?",
            correct,
            [("📈 Выше", "up"), ("📉 Ниже", "down")],
            {"rate": rate},
        )
    if job == "guard":
        faces = ["🙂", "😎", "🥸"]
        spy_idx = random.randint(0, 2)
        return (
            f"🛡 Охрана: кто шпион?\n1) {faces[0]}  2) {faces[1]}  3) {faces[2]}",
            str(spy_idx),
            [(f"1 {faces[0]}", "0"), (f"2 {faces[1]}", "1"), (f"3 {faces[2]}", "2")],
            {"faces": faces},
        )
    if job == "fish":
        correct = random.choice(["left", "right", "deep"])
        return (
            "🎣 Рыбалка: где клюёт?\nВыбери место.",
            correct,
            [("⬅ Слева", "left"), ("➡ Справа", "right"), ("⬇ Глубже", "deep")],
            {},
        )
    if job == "farm":
        correct = random.choice(["water", "weed", "harvest"])
        return (
            "🌾 Поле: что сделать сейчас?",
            correct,
            [("💧 Полить", "water"), ("🌿 Прополоть", "weed"), ("🧺 Собрать", "harvest")],
            {},
        )
    if job == "forge":
        correct = random.choice(["soft", "hard", "quench"])
        return (
            "🔥 Кузня: ударь правильно!",
            correct,
            [("🔨 Легко", "soft"), ("⚔ Сильно", "hard"), ("❄ Закалить", "quench")],
            {},
        )
    if job == "tavern":
        correct = random.choice(["ale", "song", "deal"])
        return (
            "🍺 Таверна: чем заработать чаевые?",
            correct,
            [("🍺 Эль", "ale"), ("🎵 Песня", "song"), ("🃏 Сделка", "deal")],
            {},
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

    for k, s in list(_sessions.items()):
        if s.vk_id == player.vk_id or s.expires_at < now_ts:
            _sessions.pop(k, None)

    _sessions[token] = MiniSession(
        vk_id=player.vk_id,
        job=job,
        token=token,
        correct=correct,
        expires_at=now_ts + 60,
        meta=meta,
    )
    return {"token": token, "prompt": prompt, "buttons": buttons, "job": job}


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

    game = _sessions.pop(token, None)
    if not game or game.vk_id != player.vk_id:
        raise WorkError("Мини-игра не найдена или устарела. Начни работу заново.")
    if utcnow().timestamp() > game.expires_at:
        raise WorkError("Время вышло. Попробуй работу снова.")

    skip_cd = bool(game.meta.get("free_mine"))
    spec = check_can_start_job(player, game.job, skip_cd=skip_cd)
    success = answer == game.correct
    loadout = await get_loadout(session, player)

    charge_notes: list[str] = []
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
            # сбрасываем только эффект чумы, вспышка остаётся
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

    from services.districts import market_work_bonus, temple_luck_bonus
    from services.empire import get_empire_status

    market_b = market_work_bonus(player.nation if player.nation_id else None)
    if market_b:
        gross = max(1, int(gross * (1.0 + market_b)))
        charge_notes.append(f"🛒 Рынок столицы: +{int(market_b * 100)}%")

    empire = await get_empire_status(session)
    if empire:
        gross = max(1, int(gross * (1.0 + float(empire["work_mult"]))))
        charge_notes.append(
            f"🏛 Указ Империи: +{int(empire['work_mult'] * 100)}%"
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

    await session.commit()

    if player.nation_id:
        from services.weeklies import add_progress

        await add_progress(session, player.nation_id, "jobs_total", 1)
        if tax:
            await add_progress(session, player.nation_id, "treasury_gain", tax)

    quest_extra = 0
    if "quest_x2" in loadout.charges_ready:
        name = await try_consume_charge(session, player, "quest_x2", loadout)
        if name:
            quest_extra = 1
            charge_notes.append(f"⚡ {name}: квест ×2")

    quest = await on_job_done(session, player)
    if quest_extra:
        quest = await on_job_done(session, player)

    drop_pool = spec.get("loot_pool") or game.job
    loot_m = loot_multiplier(ev, flash)
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
