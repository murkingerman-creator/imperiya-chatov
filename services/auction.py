import random
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot import config
from db.models import Nation, Player, TrophyAuction
from services.nation import get_nation_by_id
from services.player import ensure_aware, utcnow


class AuctionError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


TROPHIES = (
    "⚔ Клинок Империи",
    "👑 Корона Налётчика",
    "💎 Кристалл Казны",
    "🏛 Обломок Трона",
    "🕶 Плащ Тени",
)


async def maybe_create_trophy(
    session: AsyncSession, seller_nation: Nation
) -> TrophyAuction | None:
    if random.random() > config.TROPHY_CHANCE:
        return None
    # close previous active of this nation
    result = await session.execute(
        select(TrophyAuction).where(
            TrophyAuction.seller_nation_id == seller_nation.id,
            TrophyAuction.active.is_(True),
        )
    )
    for old in result.scalars().all():
        await _close_auction(session, old)

    item = random.choice(TROPHIES)
    auction = TrophyAuction(
        item_name=item,
        seller_nation_id=seller_nation.id,
        bid=config.AUCTION_START_BID,
        active=True,
        ends_at=utcnow() + timedelta(hours=config.AUCTION_HOURS),
    )
    session.add(auction)
    await session.commit()
    await session.refresh(auction)
    return auction


async def _close_auction(session: AsyncSession, auction: TrophyAuction) -> None:
    """Закрыть: деньги победителя → казна продавца (если была ставка)."""
    if not auction.active:
        return
    auction.active = False
    if auction.bidder_vk_id and auction.bid > 0:
        seller = await get_nation_by_id(session, auction.seller_nation_id)
        if seller:
            seller.treasury += auction.bid


async def settle_expired_auctions(session: AsyncSession) -> int:
    result = await session.execute(
        select(TrophyAuction).where(TrophyAuction.active.is_(True))
    )
    now = utcnow()
    closed = 0
    for a in result.scalars().all():
        ends = ensure_aware(a.ends_at)
        if ends and now >= ends:
            await _close_auction(session, a)
            closed += 1
    if closed:
        await session.commit()
    return closed


async def get_active_auctions(session: AsyncSession) -> list[TrophyAuction]:
    await settle_expired_auctions(session)
    result = await session.execute(
        select(TrophyAuction)
        .where(TrophyAuction.active.is_(True))
        .order_by(TrophyAuction.id.desc())
        .limit(10)
    )
    return list(result.scalars().all())


async def place_bid(
    session: AsyncSession, auction_id: int, bidder: Player, amount: int
) -> TrophyAuction:
    if not bidder.nation_id or not bidder.nation:
        raise AuctionError("Только гражданин страны может ставить.")
    if bidder.nation.leader_id != bidder.vk_id:
        raise AuctionError("Ставки делают только лидеры.")

    result = await session.execute(
        select(TrophyAuction).where(TrophyAuction.id == auction_id)
    )
    auction = result.scalar_one_or_none()
    if not auction or not auction.active:
        raise AuctionError("Аукцион не найден или закрыт.")
    ends = ensure_aware(auction.ends_at)
    if ends and utcnow() >= ends:
        auction.active = False
        await session.commit()
        raise AuctionError("Аукцион уже закончился.")

    if auction.seller_nation_id == bidder.nation_id:
        raise AuctionError("Нельзя ставить на свой трофей.")
    if amount <= auction.bid:
        raise AuctionError(f"Ставка должна быть больше {auction.bid}.")
    if bidder.crowns < amount:
        raise AuctionError("Недостаточно крон.")

    # refund previous bidder
    if auction.bidder_vk_id:
        prev = await session.execute(
            select(Player).where(Player.vk_id == auction.bidder_vk_id)
        )
        prev_p = prev.scalar_one_or_none()
        if prev_p:
            prev_p.crowns += auction.bid

    bidder.crowns -= amount
    auction.bid = amount
    auction.bidder_vk_id = bidder.vk_id
    auction.bidder_nation_id = bidder.nation_id
    await session.commit()
    await session.refresh(auction)
    return auction
