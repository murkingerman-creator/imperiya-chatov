"""Инвентарь: сумка, экипировка, слияние, продажа, кодекс."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot import config
from data import items_catalog as cat
from db.models import DiscoveredItem, EquippedItem, InventoryItem, Player
from services.achievements import grant_title
from services.player import utcnow


class InventoryError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


async def add_item(
    session: AsyncSession, player: Player, item_id: str, qty: int = 1
) -> dict:
    it = cat.get_item(item_id)
    if not it:
        raise InventoryError("Неизвестный предмет.")

    result = await session.execute(
        select(InventoryItem).where(
            InventoryItem.player_vk_id == player.vk_id,
            InventoryItem.item_id == item_id,
        )
    )
    row = result.scalar_one_or_none()
    if row:
        row.qty += qty
    else:
        session.add(
            InventoryItem(player_vk_id=player.vk_id, item_id=item_id, qty=qty)
        )

    first = await _mark_discovered(session, player.vk_id, item_id)
    titles = []
    if first and it["rarity"] == "mythic":
        t = await grant_title(session, player, "myth_finder")
        if t:
            titles.append(t)
    discovered = await discovered_count(session, player.vk_id)
    if discovered >= 30:
        t = await grant_title(session, player, "collector")
        if t:
            titles.append(t)

    await session.commit()
    return {"item": it, "first": first, "titles": titles}


async def _mark_discovered(session: AsyncSession, vk_id: int, item_id: str) -> bool:
    result = await session.execute(
        select(DiscoveredItem).where(
            DiscoveredItem.player_vk_id == vk_id,
            DiscoveredItem.item_id == item_id,
        )
    )
    if result.scalar_one_or_none():
        return False
    session.add(DiscoveredItem(player_vk_id=vk_id, item_id=item_id))
    return True


async def discovered_count(session: AsyncSession, vk_id: int) -> int:
    result = await session.execute(
        select(DiscoveredItem).where(DiscoveredItem.player_vk_id == vk_id)
    )
    return len(list(result.scalars().all()))


async def list_bag(session: AsyncSession, vk_id: int) -> list[tuple[dict, int]]:
    result = await session.execute(
        select(InventoryItem)
        .where(InventoryItem.player_vk_id == vk_id, InventoryItem.qty > 0)
        .order_by(InventoryItem.item_id)
    )
    out = []
    for row in result.scalars().all():
        it = cat.get_item(row.item_id)
        if it:
            out.append((it, row.qty))
    return out


async def get_equipped(session: AsyncSession, vk_id: int) -> dict[str, dict]:
    result = await session.execute(
        select(EquippedItem).where(EquippedItem.player_vk_id == vk_id)
    )
    equipped = {}
    for row in result.scalars().all():
        it = cat.get_item(row.item_id)
        if it:
            equipped[row.slot] = it
    return equipped


async def equip(session: AsyncSession, player: Player, item_id: str) -> dict:
    it = cat.get_item(item_id)
    if not it:
        raise InventoryError("Предмет не найден.")
    if it["slot"] not in cat.SLOTS:
        raise InventoryError("Этот предмет нельзя экипировать.")

    bag = await session.execute(
        select(InventoryItem).where(
            InventoryItem.player_vk_id == player.vk_id,
            InventoryItem.item_id == item_id,
            InventoryItem.qty > 0,
        )
    )
    if not bag.scalar_one_or_none():
        raise InventoryError("Нет такого предмета в сумке.")

    if it["rarity"] == "mythic":
        current = await get_equipped(session, player.vk_id)
        for _slot, cur in current.items():
            if cur["rarity"] == "mythic" and cur["id"] != item_id:
                raise InventoryError("Можно носить только 1 мифический предмет.")

    slot = it["slot"]
    prev = await session.execute(
        select(EquippedItem).where(
            EquippedItem.player_vk_id == player.vk_id,
            EquippedItem.slot == slot,
        )
    )
    prev_row = prev.scalar_one_or_none()
    old_id = prev_row.item_id if prev_row else None

    if prev_row:
        prev_row.item_id = item_id
    else:
        session.add(
            EquippedItem(player_vk_id=player.vk_id, slot=slot, item_id=item_id)
        )

    await _dec_bag(session, player.vk_id, item_id, 1)
    if old_id:
        await _inc_bag(session, player.vk_id, old_id, 1)

    await session.commit()
    return {
        "item": it,
        "slot": slot,
        "mythic_announce": it["rarity"] == "mythic",
    }


async def unequip(session: AsyncSession, player: Player, slot: str) -> dict:
    if slot not in cat.SLOTS:
        raise InventoryError("Неизвестный слот.")
    result = await session.execute(
        select(EquippedItem).where(
            EquippedItem.player_vk_id == player.vk_id,
            EquippedItem.slot == slot,
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        raise InventoryError("Слот пуст.")
    it = cat.get_item(row.item_id)
    await _inc_bag(session, player.vk_id, row.item_id, 1)
    await session.delete(row)
    await session.commit()
    return {"item": it, "slot": slot}


async def _inc_bag(session: AsyncSession, vk_id: int, item_id: str, qty: int) -> None:
    result = await session.execute(
        select(InventoryItem).where(
            InventoryItem.player_vk_id == vk_id,
            InventoryItem.item_id == item_id,
        )
    )
    row = result.scalar_one_or_none()
    if row:
        row.qty += qty
    else:
        session.add(InventoryItem(player_vk_id=vk_id, item_id=item_id, qty=qty))


async def _dec_bag(session: AsyncSession, vk_id: int, item_id: str, qty: int) -> None:
    result = await session.execute(
        select(InventoryItem).where(
            InventoryItem.player_vk_id == vk_id,
            InventoryItem.item_id == item_id,
        )
    )
    row = result.scalar_one_or_none()
    if not row or row.qty < qty:
        raise InventoryError("Недостаточно предметов в сумке.")
    row.qty -= qty
    if row.qty <= 0:
        await session.delete(row)


async def sell_item(session: AsyncSession, player: Player, item_id: str, qty: int = 1) -> dict:
    it = cat.get_item(item_id)
    if not it:
        raise InventoryError("Предмет не найден.")
    # cannot sell if equipped
    eq = await session.execute(
        select(EquippedItem).where(
            EquippedItem.player_vk_id == player.vk_id,
            EquippedItem.item_id == item_id,
        )
    )
    if eq.scalar_one_or_none():
        raise InventoryError("Сначала сними предмет.")
    price = cat.SELL_PRICE.get(it["rarity"], 10) * qty
    await _dec_bag(session, player.vk_id, item_id, qty)
    player.crowns += price
    await session.commit()
    return {"item": it, "qty": qty, "price": price, "crowns": player.crowns}


async def donate_item(session: AsyncSession, player: Player, item_id: str) -> dict:
    it = cat.get_item(item_id)
    if not it:
        raise InventoryError("Предмет не найден.")
    if it["rarity"] not in ("epic", "legendary", "mythic"):
        raise InventoryError("В казну можно сдать только эпик+.")
    if not player.nation:
        raise InventoryError("Нужна страна.")
    eq = await session.execute(
        select(EquippedItem).where(
            EquippedItem.player_vk_id == player.vk_id,
            EquippedItem.item_id == item_id,
        )
    )
    if eq.scalar_one_or_none():
        raise InventoryError("Сначала сними предмет.")
    amount = cat.DONATE_TREASURY.get(it["rarity"], 100)
    await _dec_bag(session, player.vk_id, item_id, 1)
    player.nation.treasury += amount
    await session.commit()
    return {"item": it, "amount": amount, "treasury": player.nation.treasury}


async def merge_commons(session: AsyncSession, player: Player, item_id: str) -> dict:
    it = cat.get_item(item_id)
    if not it or it["rarity"] != "common":
        raise InventoryError("Сливать можно только обычные.")
    need = config.MERGE_COMMON_COUNT
    result = await session.execute(
        select(InventoryItem).where(
            InventoryItem.player_vk_id == player.vk_id,
            InventoryItem.item_id == item_id,
        )
    )
    row = result.scalar_one_or_none()
    if not row or row.qty < need:
        raise InventoryError(f"Нужно {need} шт. в сумке.")

    # pick uncommon same family
    candidates = [
        x
        for x in cat.all_items()
        if x["rarity"] == "uncommon" and x["family"] == it["family"]
    ]
    if not candidates:
        candidates = [x for x in cat.all_items() if x["rarity"] == "uncommon"]
    import random

    reward = random.choice(candidates)
    row.qty -= need
    if row.qty <= 0:
        await session.delete(row)
    await add_item(session, player, reward["id"], 1)
    return {"from": it, "to": reward, "spent": need}
