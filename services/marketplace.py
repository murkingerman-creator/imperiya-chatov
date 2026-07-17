"""P2P торговая площадка предметов."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot import config
from data import items_catalog as cat
from db.models import EquippedItem, MarketListing, Player
from services.inventory import InventoryError, _dec_bag, _inc_bag, _mark_discovered
from services.player import ensure_aware, utcnow


class MarketError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


async def _expire_old(session: AsyncSession) -> None:
    result = await session.execute(
        select(MarketListing).where(MarketListing.active.is_(True))
    )
    now = utcnow()
    changed = False
    for listing in result.scalars().all():
        ends = ensure_aware(listing.ends_at)
        if ends and now >= ends:
            await _inc_bag(session, listing.seller_vk_id, listing.item_id, 1)
            listing.active = False
            changed = True
    if changed:
        await session.commit()


async def create_listing(
    session: AsyncSession, seller: Player, item_id: str, price: int
) -> MarketListing:
    it = cat.get_item(item_id)
    if not it:
        raise MarketError("Предмет не найден.")
    if price < config.MARKET_MIN_PRICE or price > config.MARKET_MAX_PRICE:
        raise MarketError(
            f"Цена {config.MARKET_MIN_PRICE}–{config.MARKET_MAX_PRICE} крон."
        )

    eq = await session.execute(
        select(EquippedItem).where(
            EquippedItem.player_vk_id == seller.vk_id,
            EquippedItem.item_id == item_id,
        )
    )
    if eq.scalar_one_or_none():
        raise MarketError("Сначала сними предмет с экипировки.")

    active = await session.execute(
        select(MarketListing).where(
            MarketListing.seller_vk_id == seller.vk_id,
            MarketListing.active.is_(True),
        )
    )
    if len(list(active.scalars().all())) >= config.MARKET_MAX_LISTINGS:
        raise MarketError(f"Максимум {config.MARKET_MAX_LISTINGS} лотов одновременно.")

    try:
        await _dec_bag(session, seller.vk_id, item_id, 1)
    except InventoryError as e:
        raise MarketError(e.message) from e

    listing = MarketListing(
        seller_vk_id=seller.vk_id,
        item_id=item_id,
        rarity=it["rarity"],
        price=price,
        active=True,
        ends_at=utcnow() + timedelta(hours=config.MARKET_HOURS),
    )
    session.add(listing)
    await session.commit()
    await session.refresh(listing)
    return listing


async def cancel_listing(session: AsyncSession, player: Player, listing_id: int) -> dict:
    result = await session.execute(
        select(MarketListing).where(MarketListing.id == listing_id)
    )
    listing = result.scalar_one_or_none()
    if not listing or not listing.active:
        raise MarketError("Лот не найден или уже закрыт.")
    if listing.seller_vk_id != player.vk_id:
        raise MarketError("Это не твой лот.")
    listing.active = False
    await _inc_bag(session, player.vk_id, listing.item_id, 1)
    await session.commit()
    it = cat.get_item(listing.item_id)
    return {"listing": listing, "item": it}


async def buy_listing(session: AsyncSession, buyer: Player, listing_id: int) -> dict:
    await _expire_old(session)
    result = await session.execute(
        select(MarketListing).where(MarketListing.id == listing_id)
    )
    listing = result.scalar_one_or_none()
    if not listing or not listing.active:
        raise MarketError("Лот не найден или уже продан.")
    ends = ensure_aware(listing.ends_at)
    if ends and utcnow() >= ends:
        listing.active = False
        await _inc_bag(session, listing.seller_vk_id, listing.item_id, 1)
        await session.commit()
        raise MarketError("Лот истёк, предмет вернулся продавцу.")

    if listing.seller_vk_id == buyer.vk_id:
        raise MarketError("Нельзя купить свой лот. Сними его в «Мои лоты».")
    if buyer.crowns < listing.price:
        raise MarketError(f"Нужно {listing.price} крон.")

    seller_res = await session.execute(
        select(Player).where(Player.vk_id == listing.seller_vk_id)
    )
    seller = seller_res.scalar_one_or_none()
    if not seller:
        raise MarketError("Продавец не найден.")

    fee = max(1, int(listing.price * config.MARKET_FEE))
    net = listing.price - fee
    buyer.crowns -= listing.price
    seller.crowns += net
    listing.active = False
    await _inc_bag(session, buyer.vk_id, listing.item_id, 1)
    first = await _mark_discovered(session, buyer.vk_id, listing.item_id)
    await session.commit()
    it = cat.get_item(listing.item_id)
    return {
        "listing": listing,
        "item": it,
        "price": listing.price,
        "fee": fee,
        "seller_got": net,
        "first": first,
        "seller": seller,
        "buyer_crowns": buyer.crowns,
    }


async def search_listings(
    session: AsyncSession,
    *,
    rarity: str | None = None,
    query: str | None = None,
    seller_vk_id: int | None = None,
    page: int = 0,
    page_size: int = 6,
) -> tuple[list[MarketListing], bool]:
    await _expire_old(session)
    result = await session.execute(
        select(MarketListing)
        .where(MarketListing.active.is_(True))
        .order_by(MarketListing.price.asc(), MarketListing.id.asc())
    )
    listings = list(result.scalars().all())
    q = (query or "").strip().casefold()
    filtered = []
    for listing in listings:
        if seller_vk_id is not None and listing.seller_vk_id != seller_vk_id:
            continue
        if rarity and listing.rarity != rarity:
            continue
        it = cat.get_item(listing.item_id)
        if not it:
            continue
        if q:
            hay = f"{it['name']} {it['id']} {it.get('desc') or ''}".casefold()
            if q not in hay:
                continue
        filtered.append(listing)

    start = max(0, page * page_size)
    chunk = filtered[start : start + page_size]
    has_next = start + page_size < len(filtered)
    return chunk, has_next


def format_listing_card(listing: MarketListing, seller_name: str | None = None) -> str:
    it = cat.get_item(listing.item_id)
    if not it:
        return f"#{listing.id} неизвестный предмет"
    seller = seller_name or str(listing.seller_vk_id)
    left = ""
    ends = ensure_aware(listing.ends_at)
    if ends:
        mins = max(0, int((ends - utcnow()).total_seconds() / 60))
        left = f" · ещё ~{mins // 60}ч {mins % 60}м"
    buffs = cat.format_buffs(it)
    return (
        f"🛒 Лот #{listing.id} — {listing.price}💰{left}\n"
        f"{cat.format_item(it)}\n"
        f"Продавец: {seller}\n"
        f"{buffs}"
    )
