"""Рабочие наборы: допуск на работы и износ."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot import config
from content import items_catalog as cat
from db.models import EquippedItem, InventoryItem, Player


def is_heavy(job: str) -> bool:
    return job in config.WORK_HEAVY_JOBS


def is_light(job: str) -> bool:
    return job in config.WORK_LIGHT_JOBS


def kit_for_job(item: dict | None) -> str | None:
    if not item:
        return None
    return item.get("work_kit_for")


async def find_kit_row(
    session: AsyncSession, player: Player, job: str
) -> InventoryItem | None:
    """Экипированный tool с work_kit_for==job, иначе первый в сумке."""
    eq = await session.execute(
        select(EquippedItem).where(
            EquippedItem.player_vk_id == player.vk_id,
            EquippedItem.slot == "tool",
        )
    )
    tool = eq.scalar_one_or_none()
    if tool:
        it = cat.get_item(tool.item_id)
        if kit_for_job(it) == job:
            inv = await session.execute(
                select(InventoryItem).where(
                    InventoryItem.player_vk_id == player.vk_id,
                    InventoryItem.item_id == tool.item_id,
                )
            )
            row = inv.scalar_one_or_none()
            if row and row.qty > 0:
                return row

    result = await session.execute(
        select(InventoryItem).where(InventoryItem.player_vk_id == player.vk_id)
    )
    for row in result.scalars().all():
        if row.qty < 1:
            continue
        it = cat.get_item(row.item_id)
        if kit_for_job(it) == job:
            return row
    return None


async def resolve_job_kit(
    session: AsyncSession, player: Player, job: str
) -> dict:
    """
    Возвращает {barehanded, kit_item_id, kit_name}.
    Тяжёлая без набора → WorkError.
    """
    row = await find_kit_row(session, player, job)
    if row:
        it = cat.get_item(row.item_id) or {}
        return {
            "barehanded": False,
            "kit_item_id": row.item_id,
            "kit_name": it.get("name", row.item_id),
        }
    if is_heavy(job):
        from services.economy import WorkError

        title = config.JOBS.get(job, {}).get("title", job)
        raise WorkError(
            f"{title}: нужен рабочий набор.\n"
            f"Открой 📦 Привоз в меню работ и купи kit для этой смены."
        )
    return {"barehanded": True, "kit_item_id": None, "kit_name": None}


async def wear_kit(
    session: AsyncSession, player: Player, item_id: str | None
) -> str | None:
    """−1 прочность. При 0 — списать 1 шт.; если стек остался — сброс прочности."""
    if not item_id:
        return None
    it = cat.get_item(item_id)
    if not it or not it.get("work_kit_for"):
        return None
    max_d = int(it.get("max_durability") or 10)

    result = await session.execute(
        select(InventoryItem).where(
            InventoryItem.player_vk_id == player.vk_id,
            InventoryItem.item_id == item_id,
        )
    )
    row = result.scalar_one_or_none()
    if not row or row.qty < 1:
        return None

    dur = row.durability if row.durability is not None else max_d
    dur -= 1
    if dur <= 0:
        row.qty -= 1
        if row.bound_qty and row.bound_qty > row.qty:
            row.bound_qty = row.qty
        if row.qty <= 0:
            # снять с экипа если было
            eq = await session.execute(
                select(EquippedItem).where(
                    EquippedItem.player_vk_id == player.vk_id,
                    EquippedItem.item_id == item_id,
                )
            )
            for e in eq.scalars().all():
                await session.delete(e)
            await session.delete(row)
            await session.flush()
            return f"🔧 {it['name']} сломался — купи новый в Привозе."
        row.durability = max_d
        await session.flush()
        return f"🔧 {it['name']} износился (осталось ×{row.qty}, прочность {max_d})."
    row.durability = dur
    await session.flush()
    return None


def format_kit_status(row: InventoryItem | None, item: dict | None) -> str:
    if not row or not item:
        return "нет"
    max_d = int(item.get("max_durability") or 10)
    dur = row.durability if row.durability is not None else max_d
    return f"{item['name']} {dur}/{max_d}" + (f" ×{row.qty}" if row.qty > 1 else "")
