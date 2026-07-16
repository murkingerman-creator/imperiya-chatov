from vkbottle.bot import Bot, Message

from bot import config
from bot.keyboards import main_keyboard
from db.database import SessionLocal
from handlers.common import resolve_name
from handlers.rules import match_cmd
from services.player import energy_next_in_minutes, get_or_create_player, regenerate_energy


def register(bot: Bot) -> None:
    @bot.on.message(func=match_cmd("profile", "профиль", "👤 профиль", "я"))
    async def profile_handler(message: Message):
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            regenerate_energy(player)
            await session.commit()

            nation_line = "не в стране"
            if player.nation:
                nation_line = f"{player.nation.flag_emoji} {player.nation.name}"
                if player.nation.leader_id == player.vk_id:
                    nation_line += " (лидер)"

            next_e = energy_next_in_minutes(player)
            energy_hint = (
                "полная"
                if next_e is None
                else f"+1 через ~{next_e} мин"
            )

            text = (
                f"👤 {player.name}\n"
                f"💰 Кроны: {player.crowns}\n"
                f"⚡ Энергия: {player.energy}/{config.MAX_ENERGY} ({energy_hint})\n"
                f"🔥 Стрик ежедневки: {player.daily_streak or 0}\n"
                f"📨 Код: {player.invite_code}\n"
                f"🏛 Страна: {nation_line}"
            )
            await message.answer(text, keyboard=main_keyboard().get_json())
