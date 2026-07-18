from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot import config
from db.models import Player
from services.item_effects import set_buff
from services.player import ensure_aware, regenerate_energy, utcnow
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


async def feast(session: AsyncSession, player: Player) -> dict:
    """Праздник: энергия гражданам + бафф работ."""
    nation = await _nation_for_treasury(session, player)
    _spend(nation, config.TREASURY_FEAST)
    feast_end = utcnow() + timedelta(hours=config.TREASURY_FEAST_HOURS)
    nation.feast_until = feast_end
    wu = ensure_aware(nation.work_buff_until)
    if not wu or wu < feast_end:
        nation.work_buff_until = feast_end
    result = await session.execute(select(Player).where(Player.nation_id == nation.id))
    citizens = list(result.scalars().all())
    boosted = 0
    for c in citizens:
        regenerate_energy(c)
        before = c.energy
        c.energy = min(config.MAX_ENERGY, c.energy + config.TREASURY_FEAST_ENERGY)
        if c.energy > before:
            boosted += 1
    await session.commit()
    return {
        "cost": config.TREASURY_FEAST,
        "boosted": boosted,
        "hours": config.TREASURY_FEAST_HOURS,
        "treasury": nation.treasury,
    }


async def fortify(session: AsyncSession, player: Player) -> dict:
    nation = await _nation_for_treasury(session, player)
    _spend(nation, config.TREASURY_FORTIFY)
    nation.fortify_until = utcnow() + timedelta(hours=config.TREASURY_FORTIFY_HOURS)
    await session.commit()
    return {
        "cost": config.TREASURY_FORTIFY,
        "hours": config.TREASURY_FORTIFY_HOURS,
        "defend_pct": int(config.TREASURY_FORTIFY_DEFEND * 100),
        "treasury": nation.treasury,
    }


async def scholarship(session: AsyncSession, player: Player) -> dict:
    nation = await _nation_for_treasury(session, player)
    _spend(nation, config.TREASURY_SCHOLAR)
    nation.xp_buff_until = utcnow() + timedelta(hours=config.TREASURY_SCHOLAR_HOURS)
    await session.commit()
    return {
        "cost": config.TREASURY_SCHOLAR,
        "hours": config.TREASURY_SCHOLAR_HOURS,
        "mult": config.TREASURY_SCHOLAR_XP_MULT,
        "treasury": nation.treasury,
    }


async def raid_fund(session: AsyncSession, player: Player) -> dict:
    nation = await _nation_for_treasury(session, player)
    _spend(nation, config.TREASURY_RAID_FUND)
    nation.raid_fund = int(nation.raid_fund or 0) + 1
    await session.commit()
    return {
        "cost": config.TREASURY_RAID_FUND,
        "charges": nation.raid_fund,
        "steal_pct": int(config.TREASURY_RAID_FUND_STEAL * 100),
        "treasury": nation.treasury,
    }


async def buy_shield_pool(session: AsyncSession, player: Player) -> dict:
    """Казна → фонд щита."""
    nation = await _nation_for_treasury(session, player)
    _spend(nation, config.TREASURY_BUY_SHIELD)
    nation.shield_pool += config.TREASURY_BUY_SHIELD_POOL
    await session.commit()
    return {
        "cost": config.TREASURY_BUY_SHIELD,
        "added": config.TREASURY_BUY_SHIELD_POOL,
        "pool": nation.shield_pool,
        "treasury": nation.treasury,
    }


async def raise_monument(session: AsyncSession, player: Player) -> dict:
    nation = await _nation_for_treasury(session, player)
    lv = int(nation.monument_level or 0)
    if lv >= config.TREASURY_MONUMENT_MAX:
        raise TreasuryError("Монумент уже максимального уровня.")
    cost = int(config.TREASURY_MONUMENT_COSTS[lv + 1])
    _spend(nation, cost)
    nation.monument_level = lv + 1
    await session.commit()
    return {
        "cost": cost,
        "level": nation.monument_level,
        "work_pct": int(nation.monument_level * config.TREASURY_MONUMENT_WORK * 100),
        "treasury": nation.treasury,
    }


def treasury_catalog_text(nation) -> str:
    from services.player import ensure_aware, utcnow

    lines = [
        f"🏛 Казна: {nation.treasury}",
        f"Фонд щита: {nation.shield_pool}/{config.NATION_SHIELD_POOL_NEED}",
        f"🗿 Монумент: ур.{int(nation.monument_level or 0)}/"
        f"{config.TREASURY_MONUMENT_MAX}",
        f"⚔ Фонд рейда: {int(nation.raid_fund or 0)} заряд(ов)",
        "",
        "Траты лидера/казначея:",
        f"• Указ {config.TREASURY_WORK_EDICT} · Сбор {config.TREASURY_WAR_LEVY}",
        f"• Раздача {config.TREASURY_PAYOUT} · Амнистия {config.TREASURY_AMNESTY}",
        f"• 🎉 Праздник {config.TREASURY_FEAST} (+энергия, работы)",
        f"• 🧱 Укрепление {config.TREASURY_FORTIFY} (защита {int(config.TREASURY_FORTIFY_DEFEND*100)}%)",
        f"• 📚 Стипендия {config.TREASURY_SCHOLAR} (XP ×{config.TREASURY_SCHOLAR_XP_MULT})",
        f"• ⚔ Фонд рейда {config.TREASURY_RAID_FUND} (+{int(config.TREASURY_RAID_FUND_STEAL*100)}% добычи)",
        f"• 🛡 Казна→щит {config.TREASURY_BUY_SHIELD} (+{config.TREASURY_BUY_SHIELD_POOL} в фонд)",
        f"• 🗿 Монумент (пост. +работы стране)",
    ]
    for attr, label in (
        ("feast_until", "🎉 Праздник"),
        ("fortify_until", "🧱 Укрепление"),
        ("xp_buff_until", "📚 Стипендия"),
    ):
        until = ensure_aware(getattr(nation, attr, None))
        if until and until > utcnow():
            left = int((until - utcnow()).total_seconds() / 60) + 1
            lines.append(f"{label} ещё ~{left} мин")
    return "\n".join(lines)
