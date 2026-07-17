import random
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from bot import config
from db.models import Nation, Player, WarLog
from services.achievements import check_after_raid, check_treasury
from services.auction import maybe_create_trophy
from services.chatwars import add_score
from services.nation import get_nation_by_id, get_nation_by_name
from services.player import ensure_aware, utcnow
from services.world_events import get_active_event, raid_cooldown, raid_multiplier


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
    ev = await get_active_event(session)
    last = ensure_aware(attacker.last_raid_at)
    cd = raid_cooldown(ev)
    if last:
        ready_at = last + cd
        if now < ready_at:
            left = (ready_at - now).total_seconds()
            if left >= 3600:
                raise WarError(f"Рейд на перезарядке. Осталось ~{left/3600:.1f} ч.")
            raise WarError(f"Рейд на перезарядке. Осталось ~{int(left/60)+1} мин.")

    defender = await get_nation_by_name(session, target_name)
    if not defender:
        raise WarError(f"Страна «{target_name}» не найдена.")

    if defender.id == attacker.id:
        raise WarError("Нельзя напасть на свою страну.")

    if defender.treasury < config.RAID_MIN_STEAL:
        raise WarError("У цели почти пустая казна — рейд невыгоден.")

    pct = random.uniform(config.RAID_STEAL_MIN_PCT, config.RAID_STEAL_MAX_PCT)
    stolen = max(config.RAID_MIN_STEAL, int(defender.treasury * pct))
    stolen = int(stolen * raid_multiplier(ev))
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

    titles = await check_after_raid(session, leader)
    titles += await check_treasury(session, leader)
    trophy = await maybe_create_trophy(session, attacker)
    await add_score(session, attacker.id, 1)

    return {
        "stolen": stolen,
        "leader_cut": leader_cut,
        "treasury_cut": treasury_cut,
        "attacker": attacker,
        "defender": defender,
        "leader_crowns": leader.crowns,
        "titles": titles,
        "trophy": trophy,
        "event": ev,
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
