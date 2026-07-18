"""Районы столицы."""

import re

from vkbottle.bot import Bot, Message

from bot.keyboards import districts_keyboard, main_keyboard, nation_keyboard
from db.database import SessionLocal
from handlers.common import is_chat_peer, reply, resolve_name
from handlers.rules import match_cmd, payload_cmd
from services.chronicle_store import add_event
from services.districts import (
    DistrictError,
    districts_status_text,
    upgrade_district,
)
from services.notify import notify_nation_chat
from services.player import get_or_create_player

DISTRICT_RE = re.compile(
    r"^(?:район|апгрейд)\s+(рынок|казарма|храм|market|barracks|temple)$",
    re.IGNORECASE,
)
_NAME_MAP = {
    "рынок": "market",
    "казарма": "barracks",
    "храм": "temple",
    "market": "market",
    "barracks": "barracks",
    "temple": "temple",
}


def register(bot: Bot) -> None:
    @bot.on.message(
        func=match_cmd("districts", "районы", "🏙 районы", "столица")
    )
    async def districts_menu(message: Message):
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            if not player.nation:
                await reply(
                    message,
                    "Сначала вступи в страну.",
                    keyboard=nation_keyboard(
                        in_chat=is_chat_peer(message.peer_id),
                        has_nation=False,
                        is_leader=False,
                    ).get_json(),
                )
                return
            text = districts_status_text(player.nation)
            await reply(
                message, text, keyboard=districts_keyboard().get_json()
            )

    @bot.on.message(func=payload_cmd("district_up"))
    async def district_up_payload(message: Message):
        payload = message.get_payload_json() or {}
        key = str(payload.get("d") or "").strip()
        if key:
            await _do_upgrade(message, key)

    @bot.on.message(
        func=lambda m: bool(DISTRICT_RE.match((m.text or "").strip()))
    )
    async def district_up_text(message: Message):
        m = DISTRICT_RE.match((message.text or "").strip())
        if not m:
            return
        key = _NAME_MAP.get(m.group(1).casefold())
        if key:
            await _do_upgrade(message, key)


async def _do_upgrade(message: Message, key: str) -> None:
    name = await resolve_name(message)
    async with SessionLocal() as session:
        player = await get_or_create_player(session, message.from_id, name)
        try:
            r = await upgrade_district(session, player, key)
        except DistrictError as e:
            await reply(
                message, e.message, keyboard=districts_keyboard().get_json()
            )
            return
        n = r["nation"]
        msg = (
            f"🏙 {r['name']} улучшен до ур. {r['level']}!\n"
            f"−{r['cost']} из казны · +{int(r['bonus'] * 100)}% {r['effect']}"
        )
        await add_event(
            session,
            "found",
            f"🏙 {n.flag_emoji} {n.name}: {r['name']} ур.{r['level']}",
            str(n.id),
        )
        await reply(message, msg, keyboard=districts_keyboard().get_json())
        await notify_nation_chat(message.ctx_api, n.chat_peer_id, msg)
