from vkbottle.bot import Bot, Message

from bot.keyboards import jobs_keyboard, main_keyboard, minigame_keyboard
from db.database import SessionLocal
from handlers.common import resolve_name
from handlers.rules import match_cmd, payload_cmd
from services.economy import WorkError, finish_minigame, start_minigame
from services.player import get_or_create_player


def register(bot: Bot) -> None:
    @bot.on.message(func=match_cmd("jobs", "работа", "💼 работа", "работы"))
    async def jobs_menu(message: Message):
        await message.answer(
            "💼 Выбери работу (у каждой свой кулдаун и мини-игра):\n"
            "⛏ Шахта — дольше, стабильно\n"
            "🛒 Рынок — чаще, риск\n"
            "🛡 Охрана — редко, жирно + казна",
            keyboard=jobs_keyboard().get_json(),
        )

    @bot.on.message(func=payload_cmd("job"))
    async def job_start(message: Message):
        payload = message.get_payload_json() or {}
        job = str(payload.get("job") or "")
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            try:
                game = start_minigame(player, job)
            except WorkError as e:
                await message.answer(e.message, keyboard=jobs_keyboard().get_json())
                return

            await message.answer(
                game["prompt"],
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
                await message.answer(e.message, keyboard=jobs_keyboard().get_json())
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

            await message.answer(
                f"{result['title']}: {status}\n"
                f"Заработано: +{result['gross']}{tax_line}{bonus_line}\n"
                f"На руки: +{result['net']}\n"
                f"💰 {result['crowns']} · ⚡ {result['energy']}",
                keyboard=main_keyboard().get_json(),
            )
