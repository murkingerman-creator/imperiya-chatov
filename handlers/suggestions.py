"""Предложения обновлений от игроков."""

import random

from vkbottle.bot import Bot, Message

from bot import config
from bot.keyboards import cancel_keyboard, main_keyboard, more_keyboard
from db.database import SessionLocal
from handlers.common import reply, resolve_name
from handlers.rules import match_cmd
from services.player import get_or_create_player
from services.suggestions import SuggestionError, create_suggestion

# from_id -> waiting for text
_pending: set[int] = set()


def register(bot: Bot) -> None:
    @bot.on.message(
        func=match_cmd(
            "suggest",
            "предложение",
            "💡 предложение",
            "идея",
            "предложить",
        )
    )
    async def suggest_ask(message: Message):
        name = await resolve_name(message)
        async with SessionLocal() as session:
            await get_or_create_player(session, message.from_id, name)
        _pending.add(message.from_id)
        await reply(
            message,
            "💡 Предложение обновления\n"
            f"Напиши идею одним сообщением "
            f"({config.SUGGESTION_MIN_LEN}–{config.SUGGESTION_MAX_LEN} символов).\n"
            f"КД между предложениями: {config.SUGGESTION_COOLDOWN_HOURS}ч.\n"
            f"За принятое — {config.SUGGESTION_REWARD} крон.\n"
            "Или «отмена».",
            keyboard=cancel_keyboard().get_json(),
        )

    @bot.on.message(blocking=False)
    async def suggest_text(message: Message):
        if message.from_id not in _pending:
            return
        if (message.get_payload_json() or {}).get("cmd"):
            return
        text = (message.text or "").strip()
        if not text:
            return
        lower = text.casefold()
        if lower in {"отмена", "❌ отмена", "cancel"}:
            _pending.discard(message.from_id)
            await reply(message, "Отменено.", keyboard=more_keyboard().get_json())
            return

        _pending.discard(message.from_id)
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            try:
                sug = await create_suggestion(session, player, text)
            except SuggestionError as e:
                await reply(
                    message,
                    e.message,
                    keyboard=more_keyboard().get_json(),
                )
                return

        # уведомить админов в ЛС
        notify = (
            f"💡 Новое предложение #{sug.id}\n"
            f"От: {sug.author_name} (id{sug.author_vk_id})\n\n"
            f"{sug.text}\n\n"
            f"!принять {sug.id}  ·  !отклонить {sug.id}"
        )
        for admin_id in config.ADMIN_IDS:
            try:
                await message.ctx_api.messages.send(
                    user_id=admin_id,
                    message=notify,
                    random_id=random.randint(1, 2_000_000_000),
                )
            except Exception:
                pass

        await reply(
            message,
            f"✅ Предложение #{sug.id} отправлено админам.\n"
            f"Если примут — получишь {config.SUGGESTION_REWARD} крон в ЛС.",
            keyboard=main_keyboard().get_json(),
        )
