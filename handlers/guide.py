"""Гайд «Как играть» и приветствие при добавлении бота в беседу."""

from vkbottle.bot import Bot, Message, rules

from bot.config import GROUP_ID
from bot.keyboards import main_keyboard
from handlers.common import GUIDE_PARTS, WELCOME_CHAT_TEXT, user_keyboard
from handlers.rules import match_cmd


def register(bot: Bot) -> None:
    @bot.on.message(
        func=match_cmd(
            "guide",
            "как играть",
            "📖 как играть",
            "гайд",
            "помощь",
            "правила",
            "о игре",
            "об игре",
            "help",
        )
    )
    async def guide_handler(message: Message):
        kb = user_keyboard(message.from_id)
        for i, part in enumerate(GUIDE_PARTS):
            # keyboard only on last part to avoid spam of keyboards
            if i == len(GUIDE_PARTS) - 1:
                await message.answer(part, keyboard=kb)
            else:
                await message.answer(part)

    @bot.on.chat_message(
        rules.ChatActionRule(["chat_invite_user", "chat_invite_user_by_link"])
    )
    async def bot_added_to_chat(message: Message):
        action = message.action
        if not action:
            return
        member_id = getattr(action, "member_id", None)
        # бота добавляют как −GROUP_ID
        if member_id != -GROUP_ID:
            return
        await message.answer(
            WELCOME_CHAT_TEXT,
            keyboard=main_keyboard().get_json(),
        )
