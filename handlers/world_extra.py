"""Сага, контракты, чёрный рынок, континент, осада, протест, реликвия."""

import re

from vkbottle.bot import Bot, Message

from bot import config
from bot.keyboards import main_keyboard, raid_targets_keyboard
from db.database import SessionLocal
from handlers.common import reply, resolve_name
from handlers.rules import match_cmd, payload_cmd
from services.black_market import black_market_text, buy_black, is_black_market_open
from services.cataclysm import format_cataclysm, get_cataclysm
from services.continents import status_text as continent_status
from services.contracts import (
    ContractError,
    JOB_LABEL,
    create_contract,
    format_contracts,
    list_contracts,
)
from services.discontent import DiscontentError, protest
from services.flash_events import get_flash_event
from services.notify import notify_nation_chat
from services.player import get_or_create_player
from services.saga import claim_saga, saga_status, start_saga
from services.shop import ShopError
from services.siege import SiegeError, siege_status, start_siege
from services.trophies import craft_nation_relic, list_trophies, trophies_line
from services.war import raid_candidates

CONTRACT_RE = re.compile(
    r"^контракт\s+(\S+)\s+(\d+)\s+(\d+)$", re.IGNORECASE
)
SIEGE_RE = re.compile(r"^(?:осада|siege)\s+(.+)$", re.IGNORECASE)
BM_RE = re.compile(r"^(?:чр|black)\s+(\S+)$", re.IGNORECASE)


def register(bot: Bot) -> None:
    @bot.on.message(func=match_cmd("saga", "сага", "📖 сага"))
    async def saga_menu(message: Message):
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            await reply(
                message,
                saga_status(player) + "\n\n«сага старт» · «сага сдать»",
                keyboard=main_keyboard().get_json(),
            )

    @bot.on.message(func=match_cmd("saga_start", "сага старт"))
    async def saga_start_h(message: Message):
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            msg = await start_saga(session, player)
            await reply(message, msg, keyboard=main_keyboard().get_json())

    @bot.on.message(func=match_cmd("saga_claim", "сага сдать", "сага сдать день"))
    async def saga_claim_h(message: Message):
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            msg = await claim_saga(session, player)
            await reply(message, msg, keyboard=main_keyboard().get_json())

    @bot.on.message(func=match_cmd("continent", "континент", "🗺 континент", "война блоков"))
    async def continent_h(message: Message):
        async with SessionLocal() as session:
            text = await continent_status(session)
            cata = await get_cataclysm(session)
            extra = format_cataclysm(cata)
            if extra:
                text += f"\n\n{extra}"
            await reply(message, text, keyboard=main_keyboard().get_json())

    @bot.on.message(func=match_cmd("protest", "протест", "😤 протест", "недовольство"))
    async def protest_h(message: Message):
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            try:
                r = await protest(session, player)
            except DiscontentError as e:
                await reply(message, e.message, keyboard=main_keyboard().get_json())
                return
            msg = f"😤 Недовольство: {r['value']}/{config.DISCONTENT_THRESHOLD}"
            if r["coup"]:
                msg += (
                    "\n🔥 Порог! В стране смута — скорее на Выборы "
                    "(Ещё → Выборы) и смените лидера!"
                )
            await reply(message, msg, keyboard=main_keyboard().get_json())
            await notify_nation_chat(
                message.ctx_api, player.nation.chat_peer_id, msg
            )

    @bot.on.message(func=match_cmd("contracts", "контракты", "📜 контракты"))
    async def contracts_h(message: Message):
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            if not player.nation:
                await reply(message, "Нужна страна.", keyboard=main_keyboard().get_json())
                return
            rows = await list_contracts(session, player.nation.id)
            text = format_contracts(rows)
            text += "\n\nЛидер: контракт mine 5 100"
            await reply(message, text, keyboard=main_keyboard().get_json())

    @bot.on.message(func=lambda m: bool(CONTRACT_RE.match((m.text or "").strip())))
    async def contract_create_h(message: Message):
        m = CONTRACT_RE.match((message.text or "").strip())
        if not m:
            return
        job, need, reward = m.group(1).lower(), int(m.group(2)), int(m.group(3))
        # алиасы
        aliases = {v: k for k, v in JOB_LABEL.items()}
        job = aliases.get(job, job)
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            try:
                row = await create_contract(session, player, job, need, reward)
            except ContractError as e:
                await reply(message, e.message, keyboard=main_keyboard().get_json())
                return
            msg = (
                f"📜 Контракт #{row.id}: {JOB_LABEL.get(job, job)} "
                f"{row.need}× → {row.reward}💰"
            )
            await reply(message, msg, keyboard=main_keyboard().get_json())
            await notify_nation_chat(
                message.ctx_api, player.nation.chat_peer_id, msg
            )

    @bot.on.message(func=match_cmd("black_market", "чёрный рынок", "черный рынок", "чр"))
    async def bm_menu(message: Message):
        async with SessionLocal() as session:
            text = await black_market_text(session)
            await reply(message, text, keyboard=main_keyboard().get_json())

    @bot.on.message(func=lambda m: bool(BM_RE.match((m.text or "").strip())))
    async def bm_buy(message: Message):
        m = BM_RE.match((message.text or "").strip())
        if not m:
            return
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            try:
                msg = await buy_black(session, player, m.group(1).strip())
            except ShopError as e:
                await reply(message, e.message, keyboard=main_keyboard().get_json())
                return
            await reply(message, msg, keyboard=main_keyboard().get_json())

    @bot.on.message(func=match_cmd("siege", "осада", "🏰 осада"))
    async def siege_menu(message: Message):
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            if not player.nation:
                await reply(message, "Нужна страна.", keyboard=main_keyboard().get_json())
                return
            st = await siege_status(session, player.nation)
            targets = await raid_candidates(session, player.nation.id)
            lines = [
                st or "🏰 Осады нет. Объяви: осада Название (3 удара / 12ч).",
                "",
                "Цель кнопкой или текстом.",
            ]
            await reply(
                message,
                "\n".join(lines),
                keyboard=raid_targets_keyboard(
                    [t.name for t in targets], cmd="siege_pick"
                ).get_json()
                if targets
                else main_keyboard().get_json(),
            )

    @bot.on.message(func=payload_cmd("siege_pick"))
    async def siege_pick(message: Message):
        payload = message.get_payload_json() or {}
        target = str(payload.get("target") or "").strip()
        if target:
            await _do_siege(message, target)

    @bot.on.message(func=lambda m: bool(SIEGE_RE.match((m.text or "").strip())))
    async def siege_text(message: Message):
        m = SIEGE_RE.match((message.text or "").strip())
        if m:
            await _do_siege(message, m.group(1).strip())

    @bot.on.message(func=match_cmd("relic_craft", "реликвия", "ковать реликвию"))
    async def relic_h(message: Message):
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            try:
                r = await craft_nation_relic(session, player)
            except ValueError as e:
                await reply(message, str(e), keyboard=main_keyboard().get_json())
                return
            n = r["nation"]
            msg = (
                f"🕯 Реликвия нации выкована в {n.flag_emoji} {n.name}!\n"
                f"+{int(r['work']*100)}% работы, +{int(r['raid']*100)}% рейд"
            )
            await reply(message, msg, keyboard=main_keyboard().get_json())
            await notify_nation_chat(message.ctx_api, n.chat_peer_id, msg)

    @bot.on.message(func=match_cmd("trophies", "трофеи", "🏷 трофеи"))
    async def trophies_h(message: Message):
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            if not player.nation:
                await reply(message, "Нужна страна.", keyboard=main_keyboard().get_json())
                return
            rows = await list_trophies(session, player.nation.id)
            await reply(
                message,
                trophies_line(rows),
                keyboard=main_keyboard().get_json(),
            )


async def _do_siege(message: Message, target: str) -> None:
    name = await resolve_name(message)
    async with SessionLocal() as session:
        player = await get_or_create_player(session, message.from_id, name)
        try:
            r = await start_siege(session, player, target)
        except SiegeError as e:
            await reply(message, e.message, keyboard=main_keyboard().get_json())
            return
        atk, dfn = r["attacker"], r["defender"]
        msg = (
            f"🏰 Осада объявлена!\n"
            f"{atk.flag_emoji} {atk.name} → {dfn.flag_emoji} {dfn.name}\n"
            f"{config.SIEGE_NEED_PROGRESS} успешных рейда за {config.SIEGE_HOURS}ч "
            f"(макс {config.SIEGE_MAX_ATTEMPTS} попыток) → куш ×2"
        )
        await reply(message, msg, keyboard=main_keyboard().get_json())
        await notify_nation_chat(message.ctx_api, atk.chat_peer_id, msg)
        await notify_nation_chat(message.ctx_api, dfn.chat_peer_id, msg)
