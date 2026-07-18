from vkbottle.bot import Bot, Message

from bot import config
from bot.keyboards import jobs_keyboard, main_keyboard, minigame_keyboard, onboarding_keyboard
from db.database import SessionLocal
from handlers.common import reply, resolve_name
from handlers.rules import match_cmd, payload_cmd
from services.announce import announce_nation
from services.economy import WorkError, finish_minigame, start_minigame
from services.item_effects import get_loadout
from services.levels import format_level_line, jobs_unlock_help, sync_level
from services.onboarding import advance_onboarding, onboarding_prompt
from services.player import get_or_create_player


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
                "💼 Работы открываются с уровнем.\n"
                f"{format_level_line(player)}\n"
                "🍺 Таверна / 🎣 Рыбалка — с 1 ур.\n"
                "🔒 = нужен уровень. Кнопка «⭐ Уровни» — полный список.\n"
                f"⚡ Энергия до {config.MAX_ENERGY}. Лут → 🎒 Сумка.",
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
                await reply(message, e.message, keyboard=jobs_keyboard(player.level or 1).get_json())
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
