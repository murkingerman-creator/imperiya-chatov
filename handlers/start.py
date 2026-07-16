from vkbottle.bot import Bot, Message

from bot.keyboards import main_keyboard
from handlers.common import MENU_TEXT, ensure_player

START_TEXTS = ("начать", "старт", "start", "меню", "📋 меню", "/start")


def register(bot: Bot) -> None:
    @bot.on.message(text=START_TEXTS)
    async def start_handler(message: Message):
        await ensure_player(message)
        await message.answer(MENU_TEXT, keyboard=main_keyboard().get_json())

    @bot.on.message(payload={"cmd": "start"})
    async def start_payload(message: Message):
        await ensure_player(message)
        await message.answer(MENU_TEXT, keyboard=main_keyboard().get_json())
