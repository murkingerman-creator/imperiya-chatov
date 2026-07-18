"""Сообщения о багах от игроков."""

import random

from vkbottle.bot import Bot, Message

from bot import config
from bot.keyboards import cancel_keyboard, main_keyboard, more_keyboard
from db.database import SessionLocal
from handlers.common import reply, resolve_name
from handlers.rules import match_cmd
from services.bugs import BugError, create_bug_report
from services.player import get_or_create_player

_pending: set[int] = set()


def register(bot: Bot) -> None:
    @bot.on.message(
        func=match_cmd(
            "bug",
            "баг",
            "🐛 баг",
            "сообщить о баге",
            "багрепорт",
            "ошибка",
        )
    )
    async def bug_ask(message: Message):
        name = await resolve_name(message)
        async with SessionLocal() as session:
            await get_or_create_player(session, message.from_id, name)
        _pending.add(message.from_id)
        await reply(
            message,
            "🐛 Сообщить о баге\n"
            "Опиши проблему одним сообщением: что делал, что ожидал, "
            f"что произошло ({config.BUG_MIN_LEN}–{config.BUG_MAX_LEN} символов).\n"
            f"КД между репортами: {config.BUG_COOLDOWN_HOURS}ч.\n"
            f"Если баг подтвердят — {config.BUG_REWARD} крон.\n"
            "Или «отмена».",
            keyboard=cancel_keyboard().get_json(),
        )

    @bot.on.message(blocking=False)
    async def bug_text(message: Message):
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
                bug = await create_bug_report(session, player, text)
            except BugError as e:
                await reply(
                    message,
                    e.message,
                    keyboard=more_keyboard().get_json(),
                )
                return

        notify = (
            f"🐛 Новый баг #{bug.id}\n"
            f"От: {bug.author_name} (id{bug.author_vk_id})\n\n"
            f"{bug.text}\n\n"
            f"!багпринять {bug.id}  ·  !баготклонить {bug.id}"
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
            f"✅ Баг #{bug.id} отправлен админам.\n"
            f"Если подтвердят — получишь {config.BUG_REWARD} крон в ЛС.",
            keyboard=main_keyboard().get_json(),
        )
