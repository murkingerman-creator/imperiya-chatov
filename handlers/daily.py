from vkbottle.bot import Bot, Message

from bot.keyboards import main_keyboard
from db.database import SessionLocal
from handlers.common import reply, resolve_name
from handlers.rules import match_cmd
from services.achievements import check_streak
from services.daily import DailyError, claim_daily
from services.player import get_or_create_player


def register(bot: Bot) -> None:
    @bot.on.message(func=match_cmd("daily", "ежедневка", "🎁 ежедневка", "бонус"))
    async def daily_handler(message: Message):
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            try:
                result = await claim_daily(session, player)
            except DailyError as e:
                await reply(message, e.message, keyboard=main_keyboard().get_json())
                return

            titles = await check_streak(session, player)
            title_line = f"\n🏅 {', '.join(titles)}" if titles else ""
            await reply(message, 
                f"🎁 Ежедневка получена!\n"
                f"+{result['reward']} крон "
                f"(база {result['base']} + стрик {result['bonus']})\n"
                f"🔥 Стрик: {result['streak']} дн.\n"
                f"💰 Баланс: {result['crowns']}{title_line}",
                keyboard=main_keyboard().get_json(),
            )
