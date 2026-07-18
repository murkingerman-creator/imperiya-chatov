"""Админ-рассылки в беседы стран и ЛС игроков."""

from __future__ import annotations

import asyncio
import logging
import random

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from vkbottle import API

from db.models import Nation, Player

logger = logging.getLogger("empire.broadcast")

PREFIX = "📢 Объявление Империи чатов\n\n"
DELAY_SEC = 0.35  # антифлуд VK

# VK: нет разрешения писать в ЛС / privacy
_DM_BLOCK_MARKERS = (
    "without permission",
    "privacy",
    "901",
    "902",
)


def _is_dm_blocked_error(exc: BaseException) -> bool:
    text = str(exc).casefold()
    return any(m in text for m in _DM_BLOCK_MARKERS)


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
    """Только те, кому ещё можно писать в ЛС."""
    result = await session.execute(
        select(Player.vk_id).where(Player.dm_ok.is_(True))
    )
    return [int(r[0]) for r in result.all()]


async def mark_dm_ok(session: AsyncSession, vk_id: int, ok: bool) -> None:
    await session.execute(
        update(Player).where(Player.vk_id == vk_id).values(dm_ok=ok)
    )


async def _send(api: API, peer_id: int, text: str) -> tuple[bool, bool]:
    """Возвращает (успех, dm_blocked)."""
    try:
        await api.messages.send(
            peer_id=peer_id,
            message=text,
            random_id=random.randint(1, 2_000_000_000),
        )
        return True, False
    except Exception as e:
        blocked = peer_id < 2_000_000_000 and _is_dm_blocked_error(e)
        if blocked:
            logger.debug("broadcast skip dm %s: no permission", peer_id)
        else:
            logger.info("broadcast to %s failed: %s", peer_id, e)
        return False, blocked


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
    skipped_dms = 0

    if to_chats:
        for peer_id in await list_chat_peer_ids(session):
            ok, _ = await _send(api, peer_id, message)
            if ok:
                ok_chats += 1
            else:
                fail_chats += 1
            await asyncio.sleep(DELAY_SEC)

    if to_dms:
        # сколько в базе «закрыли ЛС» — для отчёта
        total = await session.execute(select(Player.vk_id))
        all_ids = {int(r[0]) for r in total.all()}
        targets = await list_player_vk_ids(session)
        skipped_dms = len(all_ids) - len(targets)

        for vk_id in targets:
            ok, blocked = await _send(api, vk_id, message)
            if ok:
                ok_dms += 1
            else:
                fail_dms += 1
                if blocked:
                    await mark_dm_ok(session, vk_id, False)
            await asyncio.sleep(DELAY_SEC)
        if skipped_dms or fail_dms:
            await session.commit()

    return {
        "ok_chats": ok_chats,
        "fail_chats": fail_chats,
        "ok_dms": ok_dms,
        "fail_dms": fail_dms,
        "skipped_dms": skipped_dms,
    }


def format_report(result: dict) -> str:
    lines = ["✅ Рассылка завершена"]
    if result["ok_chats"] or result["fail_chats"]:
        lines.append(
            f"Беседы: ок {result['ok_chats']}, ошибок {result['fail_chats']}"
        )
    if result["ok_dms"] or result["fail_dms"] or result.get("skipped_dms"):
        line = f"ЛС: ок {result['ok_dms']}, ошибок {result['fail_dms']}"
        skipped = int(result.get("skipped_dms") or 0)
        if skipped:
            line += f", пропущено (нет ЛС) {skipped}"
        lines.append(line)
    return "\n".join(lines)
