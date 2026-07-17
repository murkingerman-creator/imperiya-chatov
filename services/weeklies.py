from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot import config
from db.models import Nation, NationWeekly, Player


class WeeklyError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def week_key(today: date | None = None) -> str:
    iso = (today or date.today()).isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


async def ensure_weekly(session: AsyncSession, nation: Nation) -> NationWeekly:
    key = week_key()
    result = await session.execute(
        select(NationWeekly).where(
            NationWeekly.nation_id == nation.id, NationWeekly.week_key == key
        )
    )
    weekly = result.scalar_one_or_none()
    if weekly:
        return weekly
    goals = ("jobs_total", "treasury_gain", "raid_attempts")
    goal_type = goals[sum(ord(c) for c in f"{key}:{nation.id}") % len(goals)]
    weekly = NationWeekly(
        nation_id=nation.id,
        week_key=key,
        goal_type=goal_type,
        target=config.WEEKLY_TARGETS[goal_type],
    )
    session.add(weekly)
    await session.commit()
    return weekly


async def add_progress(
    session: AsyncSession, nation_id: int, goal_type: str, amount: int
) -> NationWeekly | None:
    if amount <= 0:
        return None
    nation = await session.get(Nation, nation_id)
    if not nation:
        return None
    weekly = await ensure_weekly(session, nation)
    if weekly.goal_type == goal_type and not weekly.claimed:
        weekly.progress += amount
        await session.commit()
    return weekly


def status_text(weekly: NationWeekly) -> str:
    labels = {
        "jobs_total": "работы",
        "treasury_gain": "крон в казну",
        "raid_attempts": "рейды",
    }
    claimed = " · награда получена" if weekly.claimed else ""
    return (
        f"📅 {weekly.week_key}: {labels.get(weekly.goal_type, weekly.goal_type)} "
        f"{min(weekly.progress, weekly.target)}/{weekly.target}{claimed}"
    )


async def claim_weekly(session: AsyncSession, player: Player) -> dict:
    if not player.nation_id or not player.nation:
        raise WeeklyError("Нужна страна.")
    if player.nation.leader_id != player.vk_id:
        raise WeeklyError("Недельную награду получает только лидер.")
    weekly = await ensure_weekly(session, player.nation)
    if weekly.claimed:
        raise WeeklyError("Недельная награда уже получена.")
    if weekly.progress < weekly.target:
        raise WeeklyError("Цель недели ещё не выполнена.")
    player.nation.treasury += config.WEEKLY_REWARD_TREASURY
    weekly.claimed = True
    await session.commit()
    return {"weekly": weekly, "reward": config.WEEKLY_REWARD_TREASURY}
