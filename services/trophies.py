"""Трофейный зал и реликвия нации."""

from __future__ import annotations

import random

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot import config
from content import items_catalog as cat
from db.models import InventoryItem, Nation, NationTrophy, Player
from services.player import utcnow


async def maybe_add_trophy(
    session: AsyncSession, attacker: Nation, defender: Nation
) -> NationTrophy | None:
    if random.random() > float(config.TROPHY_HALL_CHANCE):
        return None
    legendaries = [
        it for it in cat.ITEMS.values() if it.get("rarity") in ("legendary", "mythic")
    ]
    if not legendaries:
        return None
    it = random.choice(legendaries)
    count = await session.execute(
        select(NationTrophy).where(NationTrophy.nation_id == attacker.id)
    )
    rows = list(count.scalars().all())
    if len(rows) >= config.TROPHY_HALL_MAX:
        # вытеснить самый старый
        oldest = min(rows, key=lambda r: r.id)
        await session.delete(oldest)
    row = NationTrophy(
        nation_id=attacker.id,
        item_id=it["id"],
        item_name=it["name"],
        from_nation_id=defender.id,
    )
    session.add(row)
    await session.commit()
    return row


async def list_trophies(session: AsyncSession, nation_id: int) -> list[NationTrophy]:
    result = await session.execute(
        select(NationTrophy)
        .where(NationTrophy.nation_id == nation_id)
        .order_by(NationTrophy.id.desc())
        .limit(config.TROPHY_HALL_MAX)
    )
    return list(result.scalars().all())


def trophies_line(rows: list[NationTrophy]) -> str:
    if not rows:
        return "🏷 Трофейный зал: пусто"
    names = ", ".join(r.item_name for r in rows[:5])
    extra = f" (+{len(rows) - 5})" if len(rows) > 5 else ""
    return f"🏷 Трофеи: {names}{extra}"


async def craft_nation_relic(session: AsyncSession, player: Player) -> dict:
    if not player.nation_id or not player.nation:
        raise ValueError("Нужна страна.")
    if player.nation.leader_id != player.vk_id:
        raise ValueError("Реликвию куёт только лидер.")
    if player.nation.nation_relic:
        raise ValueError("У страны уже есть реликвия.")

    result = await session.execute(
        select(InventoryItem).where(InventoryItem.player_vk_id == player.vk_id)
    )
    bag = list(result.scalars().all())
    epic_rows: list[InventoryItem] = []
    for row in bag:
        it = cat.get_item(row.item_id)
        if it and it.get("rarity") == "epic" and row.qty > 0:
            epic_rows.append(row)
    total = sum(r.qty for r in epic_rows)
    need = int(config.NATION_RELIC_EPICS)
    if total < need:
        raise ValueError(f"Нужно {need} эпиков в сумке (есть {total}).")

    left = need
    for row in epic_rows:
        if left <= 0:
            break
        take = min(row.qty, left)
        row.qty -= take
        left -= take
        if row.qty <= 0:
            await session.delete(row)

    player.nation.nation_relic = "forged_aura"
    await session.commit()
    return {
        "nation": player.nation,
        "work": config.NATION_RELIC_WORK,
        "raid": config.NATION_RELIC_RAID,
    }


def relic_bonuses(nation: Nation | None) -> tuple[float, float]:
    if not nation or not nation.nation_relic:
        return 0.0, 0.0
    return float(config.NATION_RELIC_WORK), float(config.NATION_RELIC_RAID)
