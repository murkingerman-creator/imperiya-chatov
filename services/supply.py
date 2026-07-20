"""Имперский привоз рабочих наборов (общий склад, ресток 2ч)."""

from __future__ import annotations

import json
import random
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from bot import config
from content import items_catalog as cat
from db.models import Player
from services.chronicle_store import get_meta, set_meta
from services.inventory import InventoryError, add_item
from services.player import ensure_aware, utcnow

META_WAVE_AT = "supply_wave_at"
META_WAVE_ID = "supply_wave_id"
META_STOCK = "imperial_supply"


class SupplyError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def _parse_stock(raw: str) -> list[dict]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    return [x for x in data if isinstance(x, dict) and x.get("item_id")]


def _dump_stock(stock: list[dict]) -> str:
    return json.dumps(stock, ensure_ascii=False)[:500]


async def ensure_supply_wave(session: AsyncSession) -> bool:
    """Реролл склада если прошло SUPPLY_RESTOCK_HOURS. True = новая волна."""
    raw_at = await get_meta(session, META_WAVE_AT)
    now = utcnow()
    need = True
    if raw_at:
        try:
            from datetime import datetime

            at = ensure_aware(datetime.fromisoformat(raw_at))
            if at and now - at < timedelta(hours=int(config.SUPPLY_RESTOCK_HOURS)):
                need = False
        except ValueError:
            need = True

    stock = _parse_stock(await get_meta(session, META_STOCK))
    if not need and stock:
        return False

    kits = list(config.SUPPLY_KIT_IDS)
    # всегда минимум 1 дешёвый kit
    cheap = min(kits, key=lambda i: int(config.SUPPLY_PRICES.get(i, 99)))
    n = random.randint(*config.SUPPLY_SLOT_COUNT)
    pool = [k for k in kits if k != cheap]
    random.shuffle(pool)
    chosen = [cheap] + pool[: max(0, n - 1)]
    random.shuffle(chosen)

    lo, hi = config.SUPPLY_QTY_RANGE
    wave_id = str(int(now.timestamp()))
    stock = []
    for kid in chosen:
        stock.append(
            {
                "item_id": kid,
                "qty": random.randint(lo, hi),
                "price": int(config.SUPPLY_PRICES.get(kid, 50)),
                "cap": int(config.SUPPLY_PER_PLAYER),
            }
        )

    await set_meta(session, META_STOCK, _dump_stock(stock))
    await set_meta(session, META_WAVE_AT, now.isoformat())
    await set_meta(session, META_WAVE_ID, wave_id)
    await session.commit()
    return True


async def get_wave_id(session: AsyncSession) -> str:
    await ensure_supply_wave(session)
    return await get_meta(session, META_WAVE_ID) or "0"


def _bought_key(wave_id: str, vk_id: int) -> str:
    return f"sup_b:{wave_id}:{vk_id}"[:64]


async def get_bought(session: AsyncSession, wave_id: str, vk_id: int) -> dict[str, int]:
    raw = await get_meta(session, _bought_key(wave_id, vk_id))
    if not raw:
        return {}
    out: dict[str, int] = {}
    for part in raw.split(","):
        if ":" not in part:
            continue
        k, _, v = part.partition(":")
        try:
            out[k] = int(v)
        except ValueError:
            continue
    return out


async def _set_bought(
    session: AsyncSession, wave_id: str, vk_id: int, bought: dict[str, int]
) -> None:
    parts = [f"{k}:{v}" for k, v in sorted(bought.items()) if v > 0]
    await set_meta(session, _bought_key(wave_id, vk_id), ",".join(parts)[:500])


async def list_supply(session: AsyncSession) -> dict:
    await ensure_supply_wave(session)
    stock = _parse_stock(await get_meta(session, META_STOCK))
    wave_id = await get_meta(session, META_WAVE_ID)
    raw_at = await get_meta(session, META_WAVE_AT)
    left_min = 0
    if raw_at:
        try:
            from datetime import datetime

            at = ensure_aware(datetime.fromisoformat(raw_at))
            end = at + timedelta(hours=int(config.SUPPLY_RESTOCK_HOURS))
            left_min = max(0, int((end - utcnow()).total_seconds() / 60))
        except ValueError:
            left_min = 0
    return {"stock": stock, "wave_id": wave_id, "restock_min": left_min}


async def buy_supply(session: AsyncSession, player: Player, item_id: str) -> dict:
    await ensure_supply_wave(session)
    stock = _parse_stock(await get_meta(session, META_STOCK))
    wave_id = await get_meta(session, META_WAVE_ID) or "0"
    slot = next((s for s in stock if s.get("item_id") == item_id), None)
    if not slot or int(slot.get("qty") or 0) < 1:
        raise SupplyError("Нет в наличии — подожди следующую волну привоза.")

    bought = await get_bought(session, wave_id, player.vk_id)
    cap = int(slot.get("cap") or config.SUPPLY_PER_PLAYER)
    have = int(bought.get(item_id, 0))
    if have >= cap:
        raise SupplyError(f"Лимит на эту позицию: {cap} шт. за волну.")

    price = int(slot.get("price") or config.SUPPLY_PRICES.get(item_id, 50))
    if player.crowns < price:
        raise SupplyError(f"Нужно {price} крон (у тебя {player.crowns}).")

    it = cat.get_item(item_id)
    if not it:
        raise SupplyError("Неизвестный набор.")

    player.crowns -= price
    slot["qty"] = int(slot["qty"]) - 1
    await set_meta(session, META_STOCK, _dump_stock(stock))
    bought[item_id] = have + 1
    await _set_bought(session, wave_id, player.vk_id, bought)

    max_d = int(it.get("max_durability") or 10)
    try:
        await add_item(session, player, item_id, 1, durability=max_d)
    except InventoryError as e:
        player.crowns += price
        slot["qty"] = int(slot["qty"]) + 1
        await set_meta(session, META_STOCK, _dump_stock(stock))
        bought[item_id] = have
        await _set_bought(session, wave_id, player.vk_id, bought)
        await session.commit()
        raise SupplyError(e.message) from e

    await session.commit()
    return {
        "item": it,
        "price": price,
        "crowns": player.crowns,
        "durability": max_d,
        "left": int(slot["qty"]),
        "bought": bought[item_id],
        "cap": cap,
    }


def format_supply_list(data: dict, *, bought: dict[str, int] | None = None) -> str:
    bought = bought or {}
    lines = [
        "📦 Имперский привоз рабочих наборов",
        f"Ресток через ~{data.get('restock_min', 0)} мин "
        f"(раз в {config.SUPPLY_RESTOCK_HOURS} ч).",
        f"Лимит: до {config.SUPPLY_PER_PLAYER} шт. одной позиции за волну.\n",
    ]
    stock = data.get("stock") or []
    if not stock:
        lines.append("Склад пуст.")
        return "\n".join(lines)
    for s in stock:
        it = cat.get_item(s["item_id"])
        name = it["name"] if it else s["item_id"]
        job = (it or {}).get("work_kit_for") or "?"
        title = config.JOBS.get(job, {}).get("title", job)
        b = bought.get(s["item_id"], 0)
        lines.append(
            f"• {name} ({title}) — {s['price']}🪙 · "
            f"осталось {s['qty']} · ты взял {b}/{s.get('cap', config.SUPPLY_PER_PLAYER)}"
        )
    lines.append("\nНажми набор, чтобы купить.")
    return "\n".join(lines)
