from vkbottle.bot import Bot, Message

from bot.keyboards import main_keyboard
from handlers.common import MENU_TEXT, ensure_player
from handlers.rules import match_cmd, payload_cmd

START_WORDS = {"начать", "старт", "start", "меню", "📋 меню", "/start"}


def _is_start_text(message: Message) -> bool:
    text = (message.text or "").strip().casefold()
    return text in {w.casefold() for w in START_WORDS}


async def _send_menu(message: Message) -> None:
    await ensure_player(message)
    await message.answer(MENU_TEXT, keyboard=main_keyboard().get_json())


def register(bot: Bot) -> None:
    @bot.on.message(func=_is_start_text)
    async def start_handler(message: Message):
        await _send_menu(message)

    @bot.on.message(func=payload_cmd("menu", "start"))
    async def start_payload_cmd(message: Message):
        await _send_menu(message)

    @bot.on.message(payload={"command": "start"})
    async def start_command_payload(message: Message):
        await _send_menu(message)
