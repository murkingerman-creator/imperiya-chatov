"""Гайд «Как играть» и приветствие при добавлении бота в беседу."""

import random

from vkbottle.bot import Bot, Message, rules

from bot.config import GROUP_ID
from handlers.common import (
    EMPTY_KEYBOARD,
    GUIDE_PARTS,
    WELCOME_CHAT_TEXT,
    is_chat_peer,
    reply,
    reply_chat,
    user_keyboard,
)
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
        if is_chat_peer(message.peer_id):
            try:
                for i, part in enumerate(GUIDE_PARTS):
                    kwargs = {
                        "user_id": message.from_id,
                        "message": part,
                        "random_id": random.randint(1, 2_000_000_000),
                    }
                    if i == len(GUIDE_PARTS) - 1:
                        kwargs["keyboard"] = kb
                    await message.ctx_api.messages.send(**kwargs)
                await message.answer(
                    f"[id{message.from_id}|Игрок], гайд отправлен в ЛС.",
                    keyboard=EMPTY_KEYBOARD,
                )
            except Exception:
                await reply_chat(
                    message,
                    f"[id{message.from_id}|Игрок], открой ЛС с ботом → «Начать», "
                    f"затем «Как играть».",
                )
            return

        for i, part in enumerate(GUIDE_PARTS):
            if i == len(GUIDE_PARTS) - 1:
                await reply(message, part, keyboard=kb)
            else:
                await reply(message, part)

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
        # без reply-клавиатуры — иначе у всех в беседе общие кнопки
        await reply_chat(message, WELCOME_CHAT_TEXT)
