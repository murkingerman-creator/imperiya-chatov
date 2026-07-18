from vkbottle import GroupEventType, GroupTypes
from vkbottle.bot import Bot, Message

from bot.config import is_admin
from bot.keyboards import admin_keyboard, main_keyboard, onboarding_keyboard
from db.database import SessionLocal
from handlers.common import reply, MENU_TEXT, ensure_player, user_keyboard
from handlers.rules import match_cmd, payload_cmd
from services.broadcast import mark_dm_ok
from services.onboarding import onboarding_prompt


def _is_start_text(message: Message) -> bool:
    text = (message.text or "").strip().casefold()
    return text in {"начать", "старт", "start", "меню", "📋 меню", "/start"}


async def _send_menu(message: Message) -> None:
    player = await ensure_player(message)
    prompt = onboarding_prompt(player)
    if prompt:
        text = f"{prompt}\n\n{MENU_TEXT}"
        if is_admin(message.from_id):
            text += "\n\n🛠 Тебе доступна админка."
        await reply(
            message,
            text,
            keyboard=onboarding_keyboard(player.onboarding_step or 0).get_json(),
        )
        return

    text = MENU_TEXT
    if is_admin(message.from_id):
        text += "\n\n🛠 Тебе доступна админка."
    await reply(message, text, keyboard=user_keyboard(message.from_id))


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

    @bot.on.raw_event(
        GroupEventType.MESSAGE_ALLOW, dataclass=GroupTypes.MessageAllow
    )
    async def on_message_allow(event: GroupTypes.MessageAllow):
        uid = int(event.object.user_id)
        async with SessionLocal() as session:
            await mark_dm_ok(session, uid, True)
            await session.commit()

    @bot.on.raw_event(
        GroupEventType.MESSAGE_DENY, dataclass=GroupTypes.MessageDeny
    )
    async def on_message_deny(event: GroupTypes.MessageDeny):
        uid = int(event.object.user_id)
        async with SessionLocal() as session:
            await mark_dm_ok(session, uid, False)
            await session.commit()
