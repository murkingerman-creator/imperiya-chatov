from vkbottle.bot import Message

from bot.config import is_admin
from bot.keyboards import main_keyboard
from db.database import SessionLocal
from services.player import get_or_create_player


MENU_TEXT = (
    "🏛 Империя чатов\n\n"
    "Беседа = государство. Работай, строй казну, воюй, зови друзей.\n\n"
    "• 🎁 Ежедневка · 💼 Работа (+контрабанда)\n"
    "• 🏛 Страна · 🎭 Эмоции · 📨 Инвайт\n"
    "• ⚔ Рейды · 🎲 Дуэль · 🎯 Ещё (ивент, квест, аукцион, выборы, война бесед)\n\n"
    "Добавь бота в беседу, чтобы основать страну."
)


def user_keyboard(vk_id: int) -> str:
    return main_keyboard(is_admin=is_admin(vk_id)).get_json()


async def resolve_name(message: Message) -> str:
    try:
        users = await message.ctx_api.users.get(user_ids=[message.from_id])
        if users:
            u = users[0]
            return f"{u.first_name} {u.last_name}".strip()
    except Exception:
        pass
    return f"Игрок {message.from_id}"


async def ensure_player(message: Message):
    name = await resolve_name(message)
    async with SessionLocal() as session:
        player = await get_or_create_player(session, message.from_id, name)
        await session.commit()
        return player
