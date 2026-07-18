"""Караван страны: несколько работ граждан за час → бонус в казну."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from bot import config
from db.models import Nation, Player
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
