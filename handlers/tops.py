from vkbottle.bot import Bot, Message

from bot.keyboards import main_keyboard
from db.database import SessionLocal
from handlers.common import ensure_player
from services.nation import top_nations, top_players


def register(bot: Bot) -> None:
    @bot.on.message(text=["топ", "топ стран", "🏆 топ стран"])
    async def top_nations_handler(message: Message):
        await ensure_player(message)
        async with SessionLocal() as session:
            rows = await top_nations(session, 10)
            if not rows:
                await message.answer(
                    "Пока нет стран. Оснуй первую в беседе!",
                    keyboard=main_keyboard().get_json(),
                )
                return

            lines = ["🏆 Топ стран по казне:\n"]
            medals = ["🥇", "🥈", "🥉"]
            for i, (nation, citizens) in enumerate(rows, start=1):
                mark = medals[i - 1] if i <= 3 else f"{i}."
                lines.append(
                    f"{mark} {nation.flag_emoji} {nation.name} — "
                    f"💰 {nation.treasury} | 👥 {citizens}"
                )
            await message.answer("\n".join(lines), keyboard=main_keyboard().get_json())

    @bot.on.message(text=["топ игроков", "💰 топ игроков"])
    async def top_players_handler(message: Message):
        await ensure_player(message)
        async with SessionLocal() as session:
            players = await top_players(session, 10)
            if not players:
                await message.answer(
                    "Пока никого нет. Напиши «Старт».",
                    keyboard=main_keyboard().get_json(),
                )
                return

            lines = ["💰 Топ игроков по кронам:\n"]
            medals = ["🥇", "🥈", "🥉"]
            for i, p in enumerate(players, start=1):
                mark = medals[i - 1] if i <= 3 else f"{i}."
                lines.append(f"{mark} {p.name} — {p.crowns} 💰")
            await message.answer("\n".join(lines), keyboard=main_keyboard().get_json())
