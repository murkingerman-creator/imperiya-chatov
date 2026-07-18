"""Союзы стран."""

import re

from vkbottle.bot import Bot, Message

from bot.keyboards import alliance_keyboard, nation_keyboard, raid_targets_keyboard
from db.database import SessionLocal
from handlers.common import is_chat_peer, reply, resolve_name
from handlers.rules import match_cmd, payload_cmd
from services.alliances import (
    AllianceError,
    accept_alliance,
    alliance_status_text,
    break_alliance,
    propose_alliance,
    reject_alliance,
)
from services.chronicle_store import add_event
from services.nation import list_nations_short_names
from services.notify import notify_nation_chat
from services.player import get_or_create_player

ALLY_RE = re.compile(r"^(?:союз|alliance)\s+(.+)$", re.IGNORECASE)


def _is_ally_propose_text(message: Message) -> bool:
    payload = message.get_payload_json() or {}
    if isinstance(payload, dict) and payload.get("cmd"):
        return False
    return bool(ALLY_RE.match((message.text or "").strip()))


def register(bot: Bot) -> None:
    @bot.on.message(
        func=match_cmd(
            "alliance",
            "союз",
            "🤝 союз",
            "союзы",
            "альянс",
        )
    )
    async def alliance_menu(message: Message):
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
            text = await alliance_status_text(session, player.nation)
            is_leader = player.nation.leader_id == player.vk_id
            await reply(
                message,
                text,
                keyboard=alliance_keyboard(is_leader=is_leader).get_json(),
            )

    @bot.on.message(func=payload_cmd("ally_propose"))
    async def ally_propose_ask(message: Message):
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            if not player.nation or player.nation.leader_id != player.vk_id:
                await reply(message, "Только лидер предлагает союз.")
                return
            names = await list_nations_short_names(session, exclude_id=player.nation.id)
            if not names:
                await reply(message, "Других стран нет.")
                return
            await reply(
                message,
                "🤝 Кому предложить союз?\n"
                "Напиши: союз Название\n"
                "Или выбери кнопку:",
                keyboard=raid_targets_keyboard(
                    names, cmd="ally_pick"
                ).get_json(),
            )

    @bot.on.message(func=payload_cmd("ally_pick"))
    async def ally_pick(message: Message):
        payload = message.get_payload_json() or {}
        target = str(payload.get("target") or "").strip()
        if target:
            await _do_propose(message, target)

    @bot.on.message(func=_is_ally_propose_text)
    async def ally_propose_text(message: Message):
        m = ALLY_RE.match((message.text or "").strip())
        if m:
            await _do_propose(message, m.group(1).strip())

    @bot.on.message(func=payload_cmd("ally_accept"))
    async def ally_accept(message: Message):
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            try:
                r = await accept_alliance(session, player)
            except AllianceError as e:
                await reply(
                    message,
                    e.message,
                    keyboard=alliance_keyboard(is_leader=True).get_json(),
                )
                return
            my, ally = r["nation"], r["ally"]
            await add_event(
                session,
                "alliance",
                f"🤝 Союз {my.flag_emoji} {my.name} + {ally.flag_emoji} {ally.name}",
                f"{my.id},{ally.id}",
            )
            msg = (
                f"🤝 Союз заключён!\n"
                f"{my.flag_emoji} {my.name} ⟷ {ally.flag_emoji} {ally.name}\n"
                f"В рейдах сила союзника помогает бить более сильных."
            )
            await reply(
                message,
                msg,
                keyboard=alliance_keyboard(is_leader=True).get_json(),
            )
            await notify_nation_chat(message.ctx_api, my.chat_peer_id, msg)
            await notify_nation_chat(message.ctx_api, ally.chat_peer_id, msg)

    @bot.on.message(func=payload_cmd("ally_reject"))
    async def ally_reject(message: Message):
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            try:
                r = await reject_alliance(session, player)
            except AllianceError as e:
                await reply(message, e.message)
                return
            ally = r["ally"]
            await reply(
                message,
                f"Предложение союза от {ally.flag_emoji} {ally.name} отклонено."
                if ally
                else "Предложение отклонено.",
                keyboard=alliance_keyboard(is_leader=True).get_json(),
            )

    @bot.on.message(func=payload_cmd("ally_break"))
    async def ally_break(message: Message):
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            try:
                r = await break_alliance(session, player)
            except AllianceError as e:
                await reply(message, e.message)
                return
            my, ally = r["nation"], r["ally"]
            penalty = int(r.get("penalty") or 0)
            ally_gain = int(r.get("ally_gain") or 0)
            await add_event(
                session,
                "alliance",
                f"💔 Предательство: {my.flag_emoji} {my.name} разорвали союз "
                f"с {ally.flag_emoji + ' ' + ally.name if ally else '?'}"
                + (f" (−{penalty} казны)" if penalty else ""),
                f"{my.id},{ally.id if ally else 0}",
            )
            if ally:
                msg = (
                    f"💔 Союз разорван — предательство!\n"
                    f"{my.flag_emoji} {my.name} больше не с "
                    f"{ally.flag_emoji} {ally.name}."
                )
            else:
                msg = "💔 Союз разорван."
            if penalty:
                msg += f"\nШтраф с казны: −{penalty}"
                if ally_gain:
                    msg += f" · союзнику +{ally_gain}"
                msg += f"\nКД нового союза: {r.get('cd_hours', 12)}ч."
            await reply(
                message, msg, keyboard=alliance_keyboard(is_leader=True).get_json()
            )
            await notify_nation_chat(message.ctx_api, my.chat_peer_id, msg)
            if ally:
                await notify_nation_chat(message.ctx_api, ally.chat_peer_id, msg)


async def _do_propose(message: Message, target: str) -> None:
    name = await resolve_name(message)
    async with SessionLocal() as session:
        player = await get_or_create_player(session, message.from_id, name)
        try:
            r = await propose_alliance(session, player, target)
        except AllianceError as e:
            await reply(
                message,
                e.message,
                keyboard=alliance_keyboard(is_leader=True).get_json(),
            )
            return
        my, to = r["from"], r["to"]
        await reply(
            message,
            f"📨 Предложение союза отправлено в {to.flag_emoji} {to.name}.\n"
            f"Их лидер: Союз → Принять.",
            keyboard=alliance_keyboard(is_leader=True).get_json(),
        )
        await notify_nation_chat(
            message.ctx_api,
            to.chat_peer_id,
            f"🤝 {my.flag_emoji} {my.name} предлагает союз!\n"
            f"Лидер: меню Союз → Принять.",
        )
