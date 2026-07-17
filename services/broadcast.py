"""Админ-рассылки в беседы стран и ЛС игроков."""

from __future__ import annotations

import asyncio
import logging
import random

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from vkbottle import API

from db.models import Nation, Player

logger = logging.getLogger("empire.broadcast")

PREFIX = "📢 Объявление Империи чатов\n\n"
DELAY_SEC = 0.35  # антифлуд VK


async def list_chat_peer_ids(session: AsyncSession) -> list[int]:
    result = await session.execute(select(Nation.chat_peer_id))
    peers = []
    seen: set[int] = set()
    for (peer_id,) in result.all():
        if peer_id and peer_id not in seen:
            seen.add(peer_id)
            peers.append(int(peer_id))
    return peers


async def list_player_vk_ids(session: AsyncSession) -> list[int]:
    result = await session.execute(select(Player.vk_id))
    return [int(r[0]) for r in result.all()]


async def _send(api: API, peer_id: int, text: str) -> bool:
    try:
        await api.messages.send(
            peer_id=peer_id,
            message=text,
            random_id=random.randint(1, 2_000_000_000),
        )
        return True
    except Exception as e:
        logger.info("broadcast to %s failed: %s", peer_id, e)
        return False


async def broadcast(
    api: API,
    session: AsyncSession,
    text: str,
    *,
    to_chats: bool = False,
    to_dms: bool = False,
) -> dict:
    body = (text or "").strip()
    if not body:
        raise ValueError("Пустой текст.")
    if len(body) > 3500:
        body = body[:3500] + "…"
    message = PREFIX + body

    ok_chats = fail_chats = 0
    ok_dms = fail_dms = 0

    if to_chats:
        for peer_id in await list_chat_peer_ids(session):
            if await _send(api, peer_id, message):
                ok_chats += 1
            else:
                fail_chats += 1
            await asyncio.sleep(DELAY_SEC)

    if to_dms:
        for vk_id in await list_player_vk_ids(session):
            if await _send(api, vk_id, message):
                ok_dms += 1
            else:
                fail_dms += 1
            await asyncio.sleep(DELAY_SEC)

    return {
        "ok_chats": ok_chats,
        "fail_chats": fail_chats,
        "ok_dms": ok_dms,
        "fail_dms": fail_dms,
    }


def format_report(result: dict) -> str:
    lines = ["✅ Рассылка завершена"]
    if result["ok_chats"] or result["fail_chats"]:
        lines.append(
            f"Беседы: ок {result['ok_chats']}, ошибок {result['fail_chats']}"
        )
    if result["ok_dms"] or result["fail_dms"]:
        lines.append(
            f"ЛС: ок {result['ok_dms']}, ошибок {result['fail_dms']}"
        )
    return "\n".join(lines)
