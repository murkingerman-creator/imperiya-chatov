from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot import config
from db.models import Player
from services.item_effects import set_buff
from services.player import utcnow
from services.roles import can_treasury


class TreasuryError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


async def _nation_for_treasury(session: AsyncSession, player: Player):
    if not player.nation_id or not player.nation:
        raise TreasuryError("Нужна страна.")
    if not await can_treasury(session, player):
        raise TreasuryError("Эта операция доступна только лидеру или казначею.")
    return player.nation


def _spend(nation, amount: int) -> None:
    if nation.treasury < amount:
        raise TreasuryError(f"В казне нужно {amount} крон (сейчас {nation.treasury}).")
    nation.treasury -= amount


async def work_edict(session: AsyncSession, player: Player) -> dict:
    nation = await _nation_for_treasury(session, player)
    _spend(nation, config.TREASURY_WORK_EDICT)
    nation.work_buff_until = utcnow() + timedelta(hours=config.TREASURY_WORK_BUFF_HOURS)
    await session.commit()
    return {"cost": config.TREASURY_WORK_EDICT, "until": nation.work_buff_until}


async def war_levy(session: AsyncSession, player: Player) -> dict:
    nation = await _nation_for_treasury(session, player)
    _spend(nation, config.TREASURY_WAR_LEVY)
    await set_buff(session, player.vk_id, "raid_levy", 1)
    await session.commit()
    return {
        "cost": config.TREASURY_WAR_LEVY,
        "bonus_pct": int(config.TREASURY_WAR_LEVY_BONUS * 100),
        "treasury": nation.treasury,
    }


async def payout(session: AsyncSession, player: Player) -> dict:
    nation = await _nation_for_treasury(session, player)
    result = await session.execute(
        select(Player)
        .where(Player.nation_id == nation.id)
        .order_by(Player.created_at.asc())
        .limit(10)
    )
    citizens = list(result.scalars().all())
    if not citizens:
        raise TreasuryError("В стране нет граждан для выплаты.")
    share = config.TREASURY_PAYOUT // len(citizens)
    if share < 10:
        raise TreasuryError("Казна не может выплатить минимум 10 крон каждому.")
    _spend(nation, config.TREASURY_PAYOUT)
    remainder = config.TREASURY_PAYOUT % len(citizens)
    for index, citizen in enumerate(citizens):
        citizen.crowns += share + (1 if index < remainder else 0)
    await session.commit()
    return {
        "cost": config.TREASURY_PAYOUT,
        "citizens": len(citizens),
        "share": share,
    }


async def amnesty(session: AsyncSession, player: Player) -> dict:
    nation = await _nation_for_treasury(session, player)
    _spend(nation, config.TREASURY_AMNESTY)
    result = await session.execute(select(Player).where(Player.nation_id == nation.id))
    citizens = list(result.scalars().all())
    for citizen in citizens:
        citizen.jail_until = None
    await session.commit()
    return {"cost": config.TREASURY_AMNESTY, "freed": len(citizens)}


async def contribute_shield(session: AsyncSession, player: Player) -> dict:
    if not player.nation_id or not player.nation:
        raise TreasuryError("Нужна страна.")
    amount = config.NATION_SHIELD_CONTRIB
    if player.crowns < amount:
        raise TreasuryError(f"Нужно {amount} личных крон (у тебя {player.crowns}).")
    player.crowns -= amount
    player.nation.shield_pool += amount
    await session.commit()
    return {"cost": amount, "pool": player.nation.shield_pool}


async def activate_shield(session: AsyncSession, player: Player) -> dict:
    nation = await _nation_for_treasury(session, player)
    need = config.NATION_SHIELD_POOL_NEED
    if nation.shield_pool < need:
        raise TreasuryError(f"Для щита нужно {need} в фонде (сейчас {nation.shield_pool}).")
    nation.shield_pool -= need
    nation.shield_until = utcnow() + timedelta(hours=config.NATION_SHIELD_HOURS)
    await session.commit()
    return {"spent": need, "until": nation.shield_until, "pool": nation.shield_pool}
