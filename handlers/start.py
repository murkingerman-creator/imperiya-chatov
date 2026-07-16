from vkbottle.bot import Bot, Message

from bot.keyboards import main_keyboard
from handlers.common import MENU_TEXT, ensure_player

START_WORDS = {"начать", "старт", "start", "меню", "📋 меню", "/start"}


def _is_start_text(message: Message) -> bool:
    text = (message.text or "").strip().lower()
    return text in START_WORDS


def register(bot: Bot) -> None:
    @bot.on.message(func=_is_start_text)
    async def start_handler(message: Message):
        await ensure_player(message)
        await message.answer(MENU_TEXT, keyboard=main_keyboard().get_json())

    # Стандартная кнопка «Начать» у сообществ VK
    @bot.on.message(payload={"command": "start"})
    async def start_command_payload(message: Message):
        await ensure_player(message)
        await message.answer(MENU_TEXT, keyboard=main_keyboard().get_json())

    @bot.on.message(payload={"cmd": "start"})
    async def start_cmd_payload(message: Message):
        await ensure_player(message)
        await message.answer(MENU_TEXT, keyboard=main_keyboard().get_json())
