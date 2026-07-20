"""Караван страны + бригада по одной работе."""

from __future__ import annotations

import json
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from bot import config
from db.models import Nation, Player
from services.chronicle_store import get_meta, set_meta
from services.player import ensure_aware, utcnow


async def on_nation_job(session: AsyncSession, player: Player) -> str | None:
    """Учесть работу гражданина. При пороге — награда казне."""
    if not player.nation_id or not player.nation:
        return None
    nation: Nation = player.nation
    now = utcnow()
    started = ensure_aware(getattr(nation, "caravan_started_at", None))
    window = timedelta(minutes=int(config.CARAVAN_WINDOW_MIN))
    progress = int(getattr(nation, "caravan_progress", 0) or 0)

    if not started or now - started > window:
        nation.caravan_started_at = now
        nation.caravan_progress = 1
        await session.commit()
        left = int(config.CARAVAN_NEED) - 1
        if left <= 0:
            return await _pay(session, nation)
        return f"🐪 Караван: 1/{config.CARAVAN_NEED} смен за час"

    nation.caravan_progress = progress + 1
    cur = int(nation.caravan_progress)
    need = int(config.CARAVAN_NEED)
    if cur >= need:
        return await _pay(session, nation)
    await session.commit()
    return f"🐪 Караван: {cur}/{need} смен за час"


async def _pay(session: AsyncSession, nation: Nation) -> str:
    reward = int(config.CARAVAN_TREASURY)
    nation.treasury += reward
    nation.caravan_progress = 0
    nation.caravan_started_at = utcnow()
    await session.commit()
    return f"🐪 Караван собран! В казну +{reward} крон"


async def on_brigade_job(
    session: AsyncSession, player: Player, job: str
) -> str | None:
    """3 разных игрока одной страны на одной работе за 30 мин → сундук казне."""
    if not player.nation_id:
        return None
    nid = int(player.nation_id)
    key = f"brigade:{nid}:{job}"[:64]
    now = utcnow()
    raw = await get_meta(session, key)
    data = {"t": now.isoformat(), "ids": []}
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                data = parsed
        except json.JSONDecodeError:
            pass

    started = None
    try:
        from datetime import datetime

        started = ensure_aware(datetime.fromisoformat(str(data.get("t") or "")))
    except ValueError:
        started = None

    window = timedelta(minutes=int(config.BRIGADE_WINDOW_MIN))
    ids = [int(x) for x in (data.get("ids") or []) if str(x).isdigit() or isinstance(x, int)]
    if not started or now - started > window:
        ids = [player.vk_id]
        data = {"t": now.isoformat(), "ids": ids}
        await set_meta(session, key, json.dumps(data, ensure_ascii=False)[:500])
        await session.commit()
        return (
            f"👷 Бригада ({config.JOBS.get(job, {}).get('title', job)}): "
            f"1/{config.BRIGADE_NEED}"
        )

    if player.vk_id not in ids:
        ids.append(player.vk_id)
    data = {"t": data.get("t") or now.isoformat(), "ids": ids}
    need = int(config.BRIGADE_NEED)
    if len(ids) >= need:
        nation = player.nation
        if nation:
            reward = int(config.BRIGADE_TREASURY)
            nation.treasury += reward
        await set_meta(session, key, "")
        await session.commit()
        title = config.JOBS.get(job, {}).get("title", job)
        return f"👷 Бригада собрана ({title})! В казну +{config.BRIGADE_TREASURY} крон"

    await set_meta(session, key, json.dumps(data, ensure_ascii=False)[:500])
    await session.commit()
    title = config.JOBS.get(job, {}).get("title", job)
    return f"👷 Бригада ({title}): {len(ids)}/{need}"
