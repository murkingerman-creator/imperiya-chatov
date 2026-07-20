from datetime import timedelta, timezone

from vkbottle.bot import Bot, Message

from bot import config
from bot.keyboards import (
    deep_job_keyboard,
    jobs_keyboard,
    main_keyboard,
    minigame_keyboard,
    onboarding_keyboard,
    work_path_keyboard,
)
from db.database import SessionLocal
from handlers.common import reply, resolve_name
from handlers.rules import match_cmd, payload_cmd
from services.announce import announce_nation
from services.economy import WorkError, finish_minigame, start_minigame
from services.item_effects import get_loadout
from services.levels import format_level_line, jobs_unlock_help, sync_level
from services.onboarding import advance_onboarding, onboarding_prompt
from services.player import ensure_aware, get_or_create_player, utcnow
from services.work_kits import resolve_job_kit
from services.work_orders import get_orders_view
from services.work_paths import format_path, set_path

MSK = timezone(timedelta(hours=3))


def _deep_available(player) -> bool:
    last = ensure_aware(getattr(player, "last_deep_work_at", None))
    if not last:
        return True
    return last.astimezone(MSK).date() < utcnow().astimezone(MSK).date()


def register(bot: Bot) -> None:
    @bot.on.message(func=match_cmd("jobs", "работа", "💼 работа", "работы"))
    async def jobs_menu(message: Message):
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            sync_level(player)
            await session.commit()
            await reply(
                message,
                "💼 Работы 2.0 — наборы, заказы, пути, смена дня.\n"
                f"{format_level_line(player)}\n"
                "Тяжёлые смены нужен набор из 📦 Привоза.\n"
                "Лёгкие (таверна/рыбалка/поле) можно без набора (−40%, без лута).\n"
                "В стране: караван + бригада (3 игрока на одной работе).\n"
                f"Путь: {format_path(player)} · "
                f"Смена дня: {'✅' if _deep_available(player) else '⏳ завтра'}\n"
                f"⚡ до {config.MAX_ENERGY}. Лут → 🎒 Сумка.",
                keyboard=jobs_keyboard(player.level or 1).get_json(),
            )

    @bot.on.message(func=match_cmd("levels", "уровень", "⭐ уровни", "ур"))
    async def levels_menu(message: Message):
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            sync_level(player)
            await session.commit()
            await reply(
                message,
                f"{format_level_line(player)}\n\n{jobs_unlock_help(player)}\n\n"
                "XP: работы, ежедневка, рейды, контрабанда, квесты, сага.",
                keyboard=jobs_keyboard(player.level or 1).get_json(),
            )

    @bot.on.message(
        func=match_cmd("work_orders", "заказы", "📋 заказы", "заказ дня")
    )
    async def work_orders_menu(message: Message):
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            text = await get_orders_view(session, player)
            await reply(
                message,
                text,
                keyboard=jobs_keyboard(player.level or 1).get_json(),
            )

    @bot.on.message(func=match_cmd("work_path", "путь", "🗺 путь", "ветка"))
    async def work_path_menu(message: Message):
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            await reply(
                message,
                "🗺 Путь мастерства (с ранга «ученик» по работе):\n"
                f"Сейчас: {format_path(player)}\n"
                f"+{int(config.WORK_PATH_BONUS * 100)}% к доходу выбранной ветки.\n"
                "Рыбалка: сети / гарпун · Кузня: оружие / подковы.",
                keyboard=work_path_keyboard().get_json(),
            )

    @bot.on.message(func=payload_cmd("set_path"))
    async def work_path_set(message: Message):
        payload = message.get_payload_json() or {}
        path = str(payload.get("path") or "")
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            try:
                note = set_path(player, path)
                await session.commit()
            except WorkError as e:
                await reply(
                    message,
                    e.message,
                    keyboard=work_path_keyboard().get_json(),
                )
                return
            await reply(
                message,
                note,
                keyboard=jobs_keyboard(player.level or 1).get_json(),
            )

    @bot.on.message(func=match_cmd("deep_work", "смена дня", "🌟 смена дня", "большая смена"))
    async def deep_work_menu(message: Message):
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            if not _deep_available(player):
                await reply(
                    message,
                    "🌟 Смена дня уже была сегодня (МСК). Завтра снова.",
                    keyboard=jobs_keyboard(player.level or 1).get_json(),
                )
                return
            await reply(
                message,
                "🌟 Смена дня (1 раз в сутки МСК):\n"
                "Цепочка из 3 шагов · ×2 награда · выше шанс лута.\n"
                "Выбери работу:",
                keyboard=deep_job_keyboard(player.level or 1).get_json(),
            )

    @bot.on.message(func=payload_cmd("deep_job"))
    async def deep_job_start(message: Message):
        payload = message.get_payload_json() or {}
        job = str(payload.get("job") or "")
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            if not _deep_available(player):
                await reply(
                    message,
                    "🌟 Смена дня уже была сегодня.",
                    keyboard=jobs_keyboard(player.level or 1).get_json(),
                )
                return
            try:
                kit = await resolve_job_kit(session, player, job)
                flags = {
                    "deep": True,
                    "barehanded": kit["barehanded"],
                    "kit_item_id": kit["kit_item_id"],
                }
                game = start_minigame(player, job, charge_flags=flags)
                player.last_deep_work_at = utcnow()
                await session.commit()
            except WorkError as e:
                await reply(
                    message,
                    e.message,
                    keyboard=jobs_keyboard(player.level or 1).get_json(),
                )
                return
            extra = ""
            if kit.get("kit_name"):
                extra = f"\n🔧 Набор: {kit['kit_name']}"
            elif kit.get("barehanded"):
                extra = "\n✋ Без набора (−40%, без лута)"
            await reply(
                message,
                game["prompt"] + extra,
                keyboard=minigame_keyboard(game["token"], game["buttons"]).get_json(),
            )

    @bot.on.message(func=payload_cmd("job_locked"))
    async def job_locked(message: Message):
        payload = message.get_payload_json() or {}
        req = int(payload.get("req") or 0)
        job = str(payload.get("job") or "")
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            title = config.JOBS.get(job, {}).get("title", job)
            if job == "smuggle":
                title = "🕶 Контрабанда"
                req = config.SMUGGLE_LEVEL_REQ
            await reply(
                message,
                f"🔒 {title} откроется с {req} уровня "
                f"(сейчас {int(player.level or 1)}).\n"
                f"{format_level_line(player)}",
                keyboard=jobs_keyboard(player.level or 1).get_json(),
            )

    @bot.on.message(func=payload_cmd("job"))
    async def job_start(message: Message):
        payload = message.get_payload_json() or {}
        job = str(payload.get("job") or "")
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            loadout = await get_loadout(session, player)
            skip_cd = False
            flags = {}
            if job == "mine" and "free_mine_x2" in loadout.charges_ready:
                skip_cd = True
                flags["free_mine"] = True
            try:
                kit = await resolve_job_kit(session, player, job)
                flags["barehanded"] = kit["barehanded"]
                flags["kit_item_id"] = kit["kit_item_id"]
                game = start_minigame(
                    player, job, skip_cd=skip_cd, charge_flags=flags
                )
            except WorkError as e:
                await reply(
                    message,
                    e.message,
                    keyboard=jobs_keyboard(player.level or 1).get_json(),
                )
                return

            prompt = game["prompt"]
            if flags.get("free_mine"):
                prompt += "\n⚡ Заряд: шахта без КД ×2"
            if kit.get("kit_name"):
                prompt += f"\n🔧 {kit['kit_name']}"
            elif kit.get("barehanded"):
                prompt += "\n✋ Без набора: −40% и без лута"
            await reply(
                message,
                prompt,
                keyboard=minigame_keyboard(game["token"], game["buttons"]).get_json(),
            )

    @bot.on.message(func=payload_cmd("job_answer"))
    async def job_answer(message: Message):
        payload = message.get_payload_json() or {}
        token = str(payload.get("token") or "")
        answer = str(payload.get("answer") or "")
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            try:
                result = await finish_minigame(session, player, token, answer)
            except WorkError as e:
                await reply(
                    message, e.message, keyboard=jobs_keyboard(player.level or 1).get_json()
                )
                return

            if result.get("continue"):
                await reply(
                    message,
                    result["prompt"],
                    keyboard=minigame_keyboard(
                        result["token"], result["buttons"]
                    ).get_json(),
                )
                return

            status = "Успех!" if result["success"] else "Провал…"
            tax_line = ""
            if result["tax"]:
                tax_line = (
                    f"\n🏛 Налог «{result['nation_name']}»: −{result['tax']}"
                )
            bonus_line = ""
            if result["treasury_bonus"]:
                bonus_line = f"\n➕ В казну страны: +{result['treasury_bonus']}"
            quest = result.get("quest") or {}
            quest_line = ""
            if quest:
                if quest.get("ready"):
                    quest_line = "\n📦 Квест готов — забери сундук в «Ещё»!"
                else:
                    quest_line = (
                        f"\n📦 Квест: {quest.get('progress', 0) % quest.get('needed', 3)}"
                        f"/{quest.get('needed', 3)}"
                    )
            drop = result.get("drop")
            drop_line = f"\n✨ Дроп: {drop['text']}" if drop else ""
            notes = result.get("charge_notes") or []
            notes_line = ("\n" + "\n".join(notes)) if notes else ""
            onboard = await advance_onboarding(session, player, "work")
            onboard_line = f"\n{onboard}" if onboard else ""

            drop_short = f", дроп {drop['text']}" if drop else ""
            await announce_nation(
                message.ctx_api,
                player.nation,
                f"💼 {player.name}: {result['title']} "
                f"{'✓' if result['success'] else '✗'} +{result['net']}{drop_short}",
            )
            if any("Караван собран" in n for n in notes):
                await announce_nation(
                    message.ctx_api,
                    player.nation,
                    f"🐪 Караван {player.nation.flag_emoji if player.nation else ''} "
                    f"собран трудами граждан!",
                )
            if any("Бригада собрана" in n for n in notes):
                await announce_nation(
                    message.ctx_api,
                    player.nation,
                    f"👷 Бригада закрыла смену — в казну бонус!",
                )

            step = player.onboarding_step or 0
            kb = (
                onboarding_keyboard(step).get_json()
                if step and onboarding_prompt(player)
                else main_keyboard().get_json()
            )
            await reply(
                message,
                f"{result['title']}: {status}\n"
                f"Заработано: +{result['gross']}{tax_line}{bonus_line}\n"
                f"На руки: +{result['net']}\n"
                f"💰 {result['crowns']} · ⚡ {result['energy']}"
                f"{quest_line}{drop_line}{notes_line}{onboard_line}",
                keyboard=kb,
            )
