"""Имперская лавка: трата крон (выкуп, энергия, баффы, вклад в казну)."""

from __future__ import annotations

import random

from sqlalchemy.ext.asyncio import AsyncSession

from bot import config
from content import items_catalog as cat
from db.models import Player
from services.inventory import add_item
from services.item_effects import get_buff, set_buff
from services.player import ensure_aware, regenerate_energy, utcnow


class ShopError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def jail_minutes_left(player: Player) -> int:
    until = ensure_aware(player.jail_until)
    if not until or utcnow() >= until:
        return 0
    return int((until - utcnow()).total_seconds() / 60) + 1


def bail_cost(player: Player) -> int | None:
    left = jail_minutes_left(player)
    if left <= 0:
        return None
    raw = int(config.SHOP_BAIL_BASE + left * config.SHOP_BAIL_PER_MIN)
    return max(config.SHOP_BAIL_MIN, min(config.SHOP_BAIL_MAX, raw))


def shop_catalog_text(player: Player) -> str:
    left = jail_minutes_left(player)
    bail = bail_cost(player)
    bail_line = (
        f"🔓 Выкуп из тюрьмы — {bail} крон (~{left} мин осталось)\n"
        if bail
        else "🔓 Выкуп — сейчас не в тюрьме\n"
    )
    return (
        "🏪 Имперская лавка\n"
        "Кроны можно тратить здесь — не только на торг.\n\n"
        f"{bail_line}"
        f"⚡ Эликсир энергии — {config.SHOP_ENERGY_FULL_COST} "
        f"(полная ⚡ до {config.MAX_ENERGY})\n"
        f"🍀 Печать удачи — {config.SHOP_WORK_LUCK_COST} "
        f"(+{int(config.SHOP_WORK_LUCK_BONUS * 100)}% к "
        f"{config.SHOP_WORK_LUCK_STACKS} работам)\n"
        f"🏛 Вклад в казну — {config.SHOP_TREASURY_GIFT} "
        f"(твои кроны → казна страны)\n"
        f"⚔ Знамя рейда — {config.SHOP_RAID_BLESS_COST} "
        f"(+{int(config.SHOP_RAID_BLESS_BONUS * 100)}% шанс к следующему рейду)\n"
        f"🎰 Колесо удачи — {config.SHOP_WHEEL_COST} (кроны или предмет)\n"
        f"🛡 Взнос в щит страны — {config.NATION_SHIELD_CONTRIB}\n\n"
        f"У тебя: {player.crowns} крон · ⚡ {player.energy}/{config.MAX_ENERGY}"
    )


async def buy_bail(session: AsyncSession, player: Player) -> dict:
    cost = bail_cost(player)
    if cost is None:
        raise ShopError("Ты не в тюрьме.")
    if player.crowns < cost:
        raise ShopError(f"Нужно {cost} крон (у тебя {player.crowns}).")
    left = jail_minutes_left(player)
    player.crowns -= cost
    player.jail_until = None
    await session.commit()
    return {"cost": cost, "freed_min": left, "crowns": player.crowns}


async def buy_energy_full(session: AsyncSession, player: Player) -> dict:
    regenerate_energy(player)
    cost = config.SHOP_ENERGY_FULL_COST
    if player.energy >= config.MAX_ENERGY:
        raise ShopError("Энергия уже полная.")
    if player.crowns < cost:
        raise ShopError(f"Нужно {cost} крон (у тебя {player.crowns}).")
    before = player.energy
    player.crowns -= cost
    player.energy = config.MAX_ENERGY
    player.energy_updated_at = utcnow()
    await session.commit()
    return {
        "cost": cost,
        "energy": player.energy,
        "gained": player.energy - before,
        "crowns": player.crowns,
    }


async def buy_work_luck(session: AsyncSession, player: Player) -> dict:
    cost = config.SHOP_WORK_LUCK_COST
    if player.crowns < cost:
        raise ShopError(f"Нужно {cost} крон (у тебя {player.crowns}).")
    existing = await get_buff(session, player.vk_id, "work_luck")
    if existing and existing.stacks >= config.SHOP_WORK_LUCK_STACKS * 2:
        raise ShopError("Слишком много печатей удачи — сначала потрать на работах.")
    player.crowns -= cost
    stacks = config.SHOP_WORK_LUCK_STACKS
    if existing and existing.stacks > 0:
        stacks = existing.stacks + config.SHOP_WORK_LUCK_STACKS
    await set_buff(session, player.vk_id, "work_luck", stacks)
    await session.commit()
    return {
        "cost": cost,
        "stacks": stacks,
        "bonus_pct": int(config.SHOP_WORK_LUCK_BONUS * 100),
        "crowns": player.crowns,
    }


async def buy_treasury_gift(session: AsyncSession, player: Player) -> dict:
    amount = config.SHOP_TREASURY_GIFT
    if not player.nation_id or not player.nation:
        raise ShopError("Нужна страна, чтобы вложить в казну.")
    if player.crowns < amount:
        raise ShopError(f"Нужно {amount} крон (у тебя {player.crowns}).")
    player.crowns -= amount
    player.nation.treasury += amount
    await session.commit()
    return {
        "cost": amount,
        "treasury": player.nation.treasury,
        "nation": f"{player.nation.flag_emoji} {player.nation.name}",
        "crowns": player.crowns,
    }


async def buy_raid_bless(session: AsyncSession, player: Player) -> dict:
    cost = config.SHOP_RAID_BLESS_COST
    if not player.nation_id:
        raise ShopError("Нужна страна (знамя для рейда лидера).")
    if player.nation and player.nation.leader_id != player.vk_id:
        raise ShopError("Знамя рейда покупает только лидер.")
    if player.crowns < cost:
        raise ShopError(f"Нужно {cost} крон (у тебя {player.crowns}).")
    existing = await get_buff(session, player.vk_id, "raid_bless")
    if existing and existing.stacks > 0:
        raise ShopError("Знамя уже активно — сначала сходи в рейд.")
    player.crowns -= cost
    await set_buff(session, player.vk_id, "raid_bless", 1)
    await session.commit()
    return {
        "cost": cost,
        "bonus_pct": int(config.SHOP_RAID_BLESS_BONUS * 100),
        "crowns": player.crowns,
    }


async def buy_wheel(session: AsyncSession, player: Player) -> dict:
    """Spin the imperial wheel for crowns or a randomly selected arsenal item."""
    cost = config.SHOP_WHEEL_COST
    if player.crowns < cost:
        raise ShopError(f"Нужно {cost} крон (у тебя {player.crowns}).")
    player.crowns -= cost
    reward_type = random.choices(
        ("crowns", "item"), weights=(45, 55), k=1
    )[0]
    if reward_type == "crowns":
        amount = random.choices((25, 50, 100, 200), weights=(50, 30, 15, 5), k=1)[0]
        player.crowns += amount
        await session.commit()
        return {"cost": cost, "type": "crowns", "amount": amount, "crowns": player.crowns}

    items = cat.all_items()
    weights = [config.LOOT_RARITY_WEIGHTS.get(item["rarity"], 1.0) for item in items]
    item = random.choices(items, weights=weights, k=1)[0]
    await add_item(session, player, item["id"])
    return {"cost": cost, "type": "item", "item": item, "crowns": player.crowns}
