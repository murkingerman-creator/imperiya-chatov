"""Сбор граждан перед рейдом — сила от вступивших."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot import config
from db.models import Nation, Player, RaidMusterJoin
from services.player import ensure_aware, utcnow
from services.roles import can_raid


class MusterError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


async def clear_muster(session: AsyncSession, nation_id: int) -> None:
    await session.execute(
        delete(RaidMusterJoin).where(RaidMusterJoin.nation_id == nation_id)
    )


async def open_muster(session: AsyncSession, player: Player) -> dict:
    if not player.nation_id or not player.nation:
        raise MusterError("Нужна страна.")
    if not await can_raid(session, player):
        raise MusterError("Сбор открывает лидер или воевода.")
    nation = player.nation
    until = utcnow() + timedelta(minutes=config.MUSTER_DURATION_MINUTES)
    await clear_muster(session, nation.id)
    # лидер автоматически в строю
    session.add(RaidMusterJoin(nation_id=nation.id, vk_id=player.vk_id))
    nation.muster_until = until
    await session.commit()
    return {"nation": nation, "until": until, "joined": 1}


async def join_muster(session: AsyncSession, player: Player) -> dict:
    if not player.nation_id or not player.nation:
        raise MusterError("Нужна страна.")
    nation = player.nation
    until = ensure_aware(nation.muster_until)
    if not until or until <= utcnow():
        raise MusterError("Сбора нет. Лидер: Война → Сбор.")
    existing = await session.execute(
        select(RaidMusterJoin).where(
            RaidMusterJoin.nation_id == nation.id,
            RaidMusterJoin.vk_id == player.vk_id,
        )
    )
    if existing.scalar_one_or_none():
        raise MusterError("Ты уже в строю.")
    count = await muster_count(session, nation.id)
    if count >= config.MUSTER_MAX_JOINS:
        raise MusterError("Сбор полон.")
    session.add(RaidMusterJoin(nation_id=nation.id, vk_id=player.vk_id))
    await session.commit()
    return {
        "nation": nation,
        "joined": count + 1,
        "until": until,
    }


async def muster_count(session: AsyncSession, nation_id: int) -> int:
    result = await session.execute(
        select(RaidMusterJoin).where(RaidMusterJoin.nation_id == nation_id)
    )
    return len(list(result.scalars().all()))


async def active_muster_bonus(
    session: AsyncSession, nation: Nation
) -> tuple[int, float]:
    """Число в строю и бонус к effective, если сбор ещё жив."""
    until = ensure_aware(nation.muster_until)
    if not until or until <= utcnow():
        return 0, 0.0
    n = await muster_count(session, nation.id)
    if n <= 0:
        return 0, 0.0
    return n, float(n) * float(config.MUSTER_FORCE_PER_JOIN)


async def consume_muster_after_raid(session: AsyncSession, nation: Nation) -> int:
    """После рейда закрыть сбор; вернуть число участников."""
    n, _ = await active_muster_bonus(session, nation)
    await clear_muster(session, nation.id)
    nation.muster_until = None
    return n
