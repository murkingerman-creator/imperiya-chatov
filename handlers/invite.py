from vkbottle.bot import Bot, Message

from bot.keyboards import main_keyboard
from db.database import SessionLocal
from handlers.common import resolve_name
from handlers.rules import match_cmd
from services.nation import NationError, apply_invite
from services.chronicle_store import add_event
from services.notify import notify_nation_chat
from services.player import get_or_create_player
from bot import config


def _is_invite_cmd(message: Message) -> bool:
    text = (message.text or "").strip().casefold()
    return text.startswith("инвайт ") or text.startswith("invite ")


def register(bot: Bot) -> None:
    @bot.on.message(func=match_cmd("invite", "инвайт", "📨 инвайт", "пригласить"))
    async def invite_info(message: Message):
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            await session.commit()
            nation_line = (
                f"Друг вступит в {player.nation.flag_emoji} {player.nation.name}"
                if player.nation
                else "Без страны — только личные бонусы"
            )
            await message.answer(
                f"📨 Код: {player.invite_code}\n"
                f"Друг пишет: инвайт {player.invite_code}\n\n"
                f"+{config.INVITE_INVITER_REWARD} тебе / "
                f"+{config.INVITE_INVITEE_REWARD} другу / "
                f"+{config.INVITE_TREASURY_REWARD} казне\n"
                f"{nation_line}",
                keyboard=main_keyboard().get_json(),
            )

    @bot.on.message(func=_is_invite_cmd)
    async def invite_redeem(message: Message):
        text = (message.text or "").strip()
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            await message.answer("Формат: инвайт КОД", keyboard=main_keyboard().get_json())
            return
        code = parts[1].strip()
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            try:
                result = await apply_invite(session, player, code)
            except NationError as e:
                await message.answer(e.message, keyboard=main_keyboard().get_json())
                return

            nation = result["nation"]
            extra = ""
            if nation:
                extra = (
                    f"\n🏛 {nation.flag_emoji} {nation.name}\n"
                    f"Казна +{result['treasury_reward']}"
                )
                await add_event(
                    session,
                    "invite",
                    f"{player.name} → {nation.flag_emoji} {nation.name} по инвайту",
                    str(nation.id),
                )
                await notify_nation_chat(
                    message.ctx_api,
                    nation.chat_peer_id,
                    f"📨 {player.name} вступил по инвайту!",
                )

            await message.answer(
                f"✅ Инвайт!\n+{result['invitee_reward']} тебе\n"
                f"+{result['inviter_reward']} пригласившему{extra}",
                keyboard=main_keyboard().get_json(),
            )
