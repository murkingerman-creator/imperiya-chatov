from vkbottle.bot import Bot, Message

from bot.keyboards import main_keyboard
from db.database import SessionLocal
from handlers.common import reply, ensure_player
from handlers.rules import match_cmd
from services.inventory import discovered_count
from sqlalchemy import select
from db.models import Player
from content import items_catalog as cat
from services.nation import top_nations, top_players


def register(bot: Bot) -> None:
    @bot.on.message(
        func=match_cmd("top_nations", "топ", "топ стран", "🏆 топ стран")
    )
    async def top_nations_handler(message: Message):
        await ensure_player(message)
        async with SessionLocal() as session:
            rows = await top_nations(session, 10)
            if not rows:
                await reply(message, 
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
            await reply(message, "\n".join(lines), keyboard=main_keyboard().get_json())

    @bot.on.message(
        func=match_cmd("top_players", "топ игроков", "💰 топ игроков")
    )
    async def top_players_handler(message: Message):
        await ensure_player(message)
        async with SessionLocal() as session:
            players = await top_players(session, 10)
            if not players:
                await reply(message, 
                    "Пока никого нет. Напиши «Старт».",
                    keyboard=main_keyboard().get_json(),
                )
                return

            lines = ["💰 Топ игроков по кронам:\n"]
            medals = ["🥇", "🥈", "🥉"]
            for i, p in enumerate(players, start=1):
                mark = medals[i - 1] if i <= 3 else f"{i}."
                lines.append(f"{mark} {p.name} — {p.crowns} 💰")
            await reply(message, "\n".join(lines), keyboard=main_keyboard().get_json())

    @bot.on.message(
        func=match_cmd("top_codex", "топ кодекса", "музей", "📦 топ кодекса")
    )
    async def top_codex_handler(message: Message):
        await ensure_player(message)
        async with SessionLocal() as session:
            result = await session.execute(select(Player))
            players = list(result.scalars().all())
            scored = []
            for p in players:
                n = await discovered_count(session, p.vk_id)
                if n:
                    scored.append((n, p))
            scored.sort(key=lambda x: (-x[0], x[1].id))
            if not scored:
                await reply(
                    message,
                    "Кодекс пуст — лутай предметы!",
                    keyboard=main_keyboard().get_json(),
                )
                return
            lines = [f"📦 Музей кодекса (из {cat.catalog_size()}):\n"]
            medals = ["🥇", "🥈", "🥉"]
            for i, (n, p) in enumerate(scored[:10], start=1):
                mark = medals[i - 1] if i <= 3 else f"{i}."
                lines.append(f"{mark} {p.name} — {n} предметов")
            await reply(message, "\n".join(lines), keyboard=main_keyboard().get_json())
