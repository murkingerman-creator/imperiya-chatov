import random
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from bot import config
from db.models import Nation, Player, WarLog
from services.nation import get_nation_by_id, get_nation_by_name
from services.player import ensure_aware, utcnow


class WarError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


async def raid(
    session: AsyncSession,
    leader: Player,
    target_name: str,
) -> dict:
    if not leader.nation_id or not leader.nation:
        raise WarError("Сначала вступи в страну или оснуй её.")

    attacker = await get_nation_by_id(session, leader.nation_id)
    if not attacker:
        raise WarError("Страна не найдена.")

    if attacker.leader_id != leader.vk_id:
        raise WarError("Объявлять рейд может только лидер страны.")

    now = utcnow()
    last = ensure_aware(attacker.last_raid_at)
    if last:
        ready_at = last + timedelta(hours=config.RAID_COOLDOWN_HOURS)
        if now < ready_at:
            hours_left = (ready_at - now).total_seconds() / 3600
            raise WarError(f"Рейд на перезарядке. Осталось ~{hours_left:.1f} ч.")

    defender = await get_nation_by_name(session, target_name)
    if not defender:
        raise WarError(f"Страна «{target_name}» не найдена.")

    if defender.id == attacker.id:
        raise WarError("Нельзя напасть на свою страну.")

    if defender.treasury < config.RAID_MIN_STEAL:
        raise WarError("У цели почти пустая казна — рейд невыгоден.")

    pct = random.uniform(config.RAID_STEAL_MIN_PCT, config.RAID_STEAL_MAX_PCT)
    stolen = max(config.RAID_MIN_STEAL, int(defender.treasury * pct))
    stolen = min(stolen, defender.treasury)

    leader_cut = int(stolen * config.RAID_LEADER_SHARE)
    treasury_cut = stolen - leader_cut

    defender.treasury -= stolen
    attacker.treasury += treasury_cut
    leader.crowns += leader_cut
    attacker.last_raid_at = now

    session.add(
        WarLog(
            attacker_nation_id=attacker.id,
            defender_nation_id=defender.id,
            amount=stolen,
        )
    )
    await session.commit()

    return {
        "stolen": stolen,
        "leader_cut": leader_cut,
        "treasury_cut": treasury_cut,
        "attacker": attacker,
        "defender": defender,
        "leader_crowns": leader.crowns,
    }


async def raid_candidates(session: AsyncSession, exclude_nation_id: int, limit: int = 6) -> list[Nation]:
    from sqlalchemy import select

    result = await session.execute(
        select(Nation)
        .where(Nation.id != exclude_nation_id, Nation.treasury >= config.RAID_MIN_STEAL)
        .order_by(Nation.treasury.desc())
        .limit(limit)
    )
    return list(result.scalars().all())
