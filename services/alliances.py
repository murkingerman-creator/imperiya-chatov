"""Союзы стран: вместе сильнее в рейде."""

from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot import config
from db.models import Nation, NationAlliance, Player
from services.nation import find_nations_fuzzy, get_nation_by_id
from services.player import ensure_aware, utcnow
from datetime import timedelta


class AllianceError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def _pair_ids(a: int, b: int) -> tuple[int, int]:
    return (a, b) if a < b else (b, a)


async def get_active_ally(
    session: AsyncSession, nation_id: int
) -> Nation | None:
    result = await session.execute(
        select(NationAlliance).where(
            NationAlliance.status == "active",
            or_(
                NationAlliance.nation_low_id == nation_id,
                NationAlliance.nation_high_id == nation_id,
            ),
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        return None
    other_id = (
        row.nation_high_id if row.nation_low_id == nation_id else row.nation_low_id
    )
    return await get_nation_by_id(session, other_id)


async def are_allied(session: AsyncSession, a_id: int, b_id: int) -> bool:
    if a_id == b_id:
        return False
    low, high = _pair_ids(a_id, b_id)
    result = await session.execute(
        select(NationAlliance).where(
            NationAlliance.status == "active",
            NationAlliance.nation_low_id == low,
            NationAlliance.nation_high_id == high,
        )
    )
    return result.scalar_one_or_none() is not None


async def list_pending_for(
    session: AsyncSession, nation_id: int
) -> list[NationAlliance]:
    result = await session.execute(
        select(NationAlliance).where(
            NationAlliance.status == "pending",
            or_(
                NationAlliance.nation_low_id == nation_id,
                NationAlliance.nation_high_id == nation_id,
            ),
        )
    )
    return list(result.scalars().all())


def _require_leader(player: Player) -> Nation:
    if not player.nation_id or not player.nation:
        raise AllianceError("Сначала вступи в страну.")
    if player.nation.leader_id != player.vk_id:
        raise AllianceError("Союзы заключает только лидер.")
    return player.nation


async def propose_alliance(
    session: AsyncSession, leader: Player, target_name: str
) -> dict:
    my = _require_leader(leader)
    cd = ensure_aware(my.alliance_cd_until)
    if cd and cd > utcnow():
        left = (cd - utcnow()).total_seconds() / 3600
        raise AllianceError(
            f"После разрыва союза КД ~{left:.1f} ч. Подожди."
        )
    matches = await find_nations_fuzzy(session, target_name)
    if not matches:
        raise AllianceError(f"Страна «{target_name}» не найдена.")
    if len(matches) > 1:
        names = ", ".join(n.name for n in matches[:5])
        raise AllianceError(f"Уточни название: {names}")
    target = matches[0]
    if target.id == my.id:
        raise AllianceError("Нельзя заключить союз с собой.")

    tcd = ensure_aware(target.alliance_cd_until)
    if tcd and tcd > utcnow():
        raise AllianceError("У этой страны ещё КД после разрыва союза.")

    if await get_active_ally(session, my.id):
        raise AllianceError("У тебя уже есть активный союз. Сначала разорви его.")
    if await get_active_ally(session, target.id):
        raise AllianceError("У этой страны уже есть союз.")

    low, high = _pair_ids(my.id, target.id)
    existing = await session.execute(
        select(NationAlliance).where(
            NationAlliance.nation_low_id == low,
            NationAlliance.nation_high_id == high,
            NationAlliance.status.in_(("pending", "active")),
        )
    )
    if existing.scalar_one_or_none():
        raise AllianceError("Предложение уже есть или союз уже действует.")

    pending = await list_pending_for(session, my.id)
    if len(pending) >= config.ALLIANCE_MAX_PENDING:
        raise AllianceError("Слишком много открытых предложений союза.")

    row = NationAlliance(
        nation_low_id=low,
        nation_high_id=high,
        status="pending",
        proposed_by_id=my.id,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return {"alliance": row, "from": my, "to": target}


async def accept_alliance(session: AsyncSession, leader: Player) -> dict:
    my = _require_leader(leader)
    if await get_active_ally(session, my.id):
        raise AllianceError("У тебя уже есть активный союз.")

    pending = await list_pending_for(session, my.id)
    # принять входящее (предложенное не нами)
    incoming = [p for p in pending if p.proposed_by_id != my.id]
    if not incoming:
        raise AllianceError("Нет входящих предложений союза.")
    row = incoming[0]
    other_id = (
        row.nation_high_id if row.nation_low_id == my.id else row.nation_low_id
    )
    if await get_active_ally(session, other_id):
        raise AllianceError("У другой стороны уже появился союз.")

    # закрыть прочие pending этой пары/сторон
    all_pending = await session.execute(
        select(NationAlliance).where(
            NationAlliance.status == "pending",
            or_(
                NationAlliance.nation_low_id.in_((my.id, other_id)),
                NationAlliance.nation_high_id.in_((my.id, other_id)),
            ),
        )
    )
    for p in all_pending.scalars().all():
        if p.id == row.id:
            continue
        await session.delete(p)

    row.status = "active"
    row.accepted_at = utcnow()
    await session.commit()
    ally = await get_nation_by_id(session, other_id)
    return {"alliance": row, "nation": my, "ally": ally}


async def reject_alliance(session: AsyncSession, leader: Player) -> dict:
    my = _require_leader(leader)
    pending = await list_pending_for(session, my.id)
    incoming = [p for p in pending if p.proposed_by_id != my.id]
    if not incoming:
        raise AllianceError("Нет входящих предложений.")
    row = incoming[0]
    other_id = (
        row.nation_high_id if row.nation_low_id == my.id else row.nation_low_id
    )
    ally = await get_nation_by_id(session, other_id)
    await session.delete(row)
    await session.commit()
    return {"nation": my, "ally": ally}


async def break_alliance(session: AsyncSession, leader: Player) -> dict:
    my = _require_leader(leader)
    result = await session.execute(
        select(NationAlliance).where(
            NationAlliance.status == "active",
            or_(
                NationAlliance.nation_low_id == my.id,
                NationAlliance.nation_high_id == my.id,
            ),
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        raise AllianceError("Активного союза нет.")
    other_id = (
        row.nation_high_id if row.nation_low_id == my.id else row.nation_low_id
    )
    ally = await get_nation_by_id(session, other_id)

    # предательство: штраф с казны инициатора
    penalty = int(my.treasury * float(config.ALLIANCE_BREAK_PENALTY_PCT))
    ally_gain = 0
    if penalty > 0:
        my.treasury -= penalty
        if ally:
            ally_gain = int(penalty * float(config.ALLIANCE_BREAK_ALLY_SHARE))
            ally.treasury += ally_gain

    cd_until = utcnow() + timedelta(hours=config.ALLIANCE_REPROPOSE_HOURS)
    my.alliance_cd_until = cd_until
    if ally:
        ally.alliance_cd_until = cd_until

    await session.delete(row)
    await session.commit()
    return {
        "nation": my,
        "ally": ally,
        "penalty": penalty,
        "ally_gain": ally_gain,
        "cd_hours": config.ALLIANCE_REPROPOSE_HOURS,
    }


async def alliance_status_text(session: AsyncSession, nation: Nation) -> str:
    ally = await get_active_ally(session, nation.id)
    lines = ["🤝 Союзы"]
    if ally:
        lines.append(
            f"Активный союз: {ally.flag_emoji} {ally.name}\n"
            f"В рейде союзник даёт ~{int(config.ALLIANCE_FORCE_SHARE * 100)}% силы "
            f"и получает {int(config.ALLIANCE_LOOT_SHARE * 100)}% добычи в казну.\n"
            f"На союзника рейдить нельзя.\n"
            f"⚠ Разрыв = предательство: −{int(config.ALLIANCE_BREAK_PENALTY_PCT * 100)}% "
            f"казны + КД {config.ALLIANCE_REPROPOSE_HOURS}ч."
        )
    else:
        lines.append("Активного союза нет.")

    pending = await list_pending_for(session, nation.id)
    if pending:
        lines.append("")
        lines.append("Ожидают:")
        for p in pending:
            other_id = (
                p.nation_high_id if p.nation_low_id == nation.id else p.nation_low_id
            )
            other = await get_nation_by_id(session, other_id)
            name = f"{other.flag_emoji} {other.name}" if other else f"#{other_id}"
            if p.proposed_by_id == nation.id:
                lines.append(f"• исходящее → {name}")
            else:
                lines.append(f"• входящее ← {name} (можно принять)")
    lines.append("")
    lines.append(
        "Лидер: предложить «союз Название», принять, отклонить или разорвать."
    )
    return "\n".join(lines)
