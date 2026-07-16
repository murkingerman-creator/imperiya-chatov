from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db.models import Nation, Player
from services.player import utcnow


class AdminError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


async def stats(session: AsyncSession) -> str:
    players = int(
        (await session.execute(select(func.count()).select_from(Player))).scalar_one()
    )
    nations = int(
        (await session.execute(select(func.count()).select_from(Nation))).scalar_one()
    )
    crowns = int(
        (await session.execute(select(func.coalesce(func.sum(Player.crowns), 0)))).scalar_one()
    )
    treasury = int(
        (await session.execute(select(func.coalesce(func.sum(Nation.treasury), 0)))).scalar_one()
    )
    return (
        f"📊 Статистика\n"
        f"Игроков: {players}\n"
        f"Стран: {nations}\n"
        f"Крон у игроков: {crowns}\n"
        f"Казны стран: {treasury}"
    )


async def get_player_info(session: AsyncSession, vk_id: int) -> str:
    result = await session.execute(
        select(Player).options(selectinload(Player.nation)).where(Player.vk_id == vk_id)
    )
    p = result.scalar_one_or_none()
    if not p:
        raise AdminError(f"Игрок {vk_id} не найден в БД.")
    nation = "нет"
    if p.nation:
        nation = f"{p.nation.flag_emoji} {p.nation.name} (id={p.nation.id})"
        if p.nation.leader_id == p.vk_id:
            nation += " [лидер]"
    return (
        f"👤 {p.name}\n"
        f"vk_id: {p.vk_id}\n"
        f"💰 {p.crowns} · ⚡ {p.energy}\n"
        f"🔥 стрик {p.daily_streak}\n"
        f"📨 {p.invite_code}\n"
        f"🏛 {nation}"
    )


async def give_crowns(session: AsyncSession, vk_id: int, amount: int) -> Player:
    result = await session.execute(
        select(Player).where(Player.vk_id == vk_id)
    )
    p = result.scalar_one_or_none()
    if not p:
        raise AdminError(f"Игрок {vk_id} не найден.")
    p.crowns += amount
    await session.commit()
    return p


async def fill_energy(session: AsyncSession, vk_id: int) -> Player:
    from bot import config

    result = await session.execute(select(Player).where(Player.vk_id == vk_id))
    p = result.scalar_one_or_none()
    if not p:
        raise AdminError(f"Игрок {vk_id} не найден.")
    p.energy = config.MAX_ENERGY
    p.energy_updated_at = utcnow()
    await session.commit()
    return p


async def reset_cooldowns(session: AsyncSession, vk_id: int) -> Player:
    result = await session.execute(select(Player).where(Player.vk_id == vk_id))
    p = result.scalar_one_or_none()
    if not p:
        raise AdminError(f"Игрок {vk_id} не найден.")
    p.last_work_at = None
    p.last_mine_at = None
    p.last_market_at = None
    p.last_guard_at = None
    p.last_daily_at = None
    p.nation_left_at = None
    await session.commit()
    return p


async def list_nations_short(session: AsyncSession, limit: int = 15) -> str:
    result = await session.execute(
        select(Nation).order_by(Nation.treasury.desc()).limit(limit)
    )
    nations = list(result.scalars().all())
    if not nations:
        return "Стран нет."
    lines = ["🏛 Страны:"]
    for n in nations:
        lines.append(f"• {n.flag_emoji} {n.name} (id={n.id}) казна={n.treasury}")
    return "\n".join(lines)
