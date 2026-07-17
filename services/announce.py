"""Анонсы действий граждан в беседу страны (с антиспамом)."""

import logging
import time

from vkbottle import API

from bot import config
from db.models import Nation
from services.notify import notify_nation_chat

logger = logging.getLogger("empire.announce")

_last_send: dict[int, float] = {}
_pending: dict[int, list[str]] = {}


async def announce_nation(api: API, nation: Nation | None, text: str) -> None:
    if not nation or not nation.chat_peer_id:
        return
    nid = nation.id
    now = time.time()
    last = _last_send.get(nid, 0)
    if now - last < config.NATION_ANNOUNCE_COOLDOWN_SEC:
        bucket = _pending.setdefault(nid, [])
        if len(bucket) < 5:
            bucket.append(text)
        return

    lines = [text]
    pending = _pending.pop(nid, [])
    lines.extend(pending[:3])
    _last_send[nid] = now
    await notify_nation_chat(api, nation.chat_peer_id, "\n".join(lines))
