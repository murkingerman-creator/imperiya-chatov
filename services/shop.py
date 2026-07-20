"""Имперская лавка: роли Быт / Война / Престиж."""

from __future__ import annotations

import random
from datetime import timedelta

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


def shop_root_text(player: Player) -> str:
    regenerate_energy(player)
    return (
        "🏪 Имперская лавка — реформа крон\n\n"
        "Крона больше не «просто число». Трать по ролям:\n"
        "🏠 Быт — жить и работать\n"
        "⚔ Война — бить и защищаться\n"
        "👑 Престиж — казна, слава, азарт\n\n"
        f"💰 У тебя: {player.crowns} крон · "
        f"⚡ {player.energy}/{config.MAX_ENERGY}"
    )


def shop_catalog_byt(player: Player) -> str:
    left = jail_minutes_left(player)
    bail = bail_cost(player)
    bail_line = (
        f"🔓 Выкуп из тюрьмы — {bail} крон (~{left} мин)\n"
        if bail
        else "🔓 Выкуп — сейчас не в тюрьме\n"
    )
    return (
        "🏠 Быт — зачем: энергия, свобода, удача на работах\n\n"
        f"{bail_line}"
        f"⚡ Эликсир энергии — {config.SHOP_ENERGY_FULL_COST} "
        f"(полная ⚡ до {config.MAX_ENERGY})\n"
        f"🍀 Печать удачи — {config.SHOP_WORK_LUCK_COST} "
        f"(+{int(config.SHOP_WORK_LUCK_BONUS * 100)}% × "
        f"{config.SHOP_WORK_LUCK_STACKS} работ)\n\n"
        f"💰 {player.crowns} · ⚡ {player.energy}/{config.MAX_ENERGY}"
    )


def shop_catalog_war(player: Player) -> str:
    return (
        "⚔ Война — зачем: шанс рейда и щит страны\n\n"
        f"⚔ Знамя рейда — {config.SHOP_RAID_BLESS_COST} "
        f"(лидер: +{int(config.SHOP_RAID_BLESS_BONUS * 100)}% к следующему рейду)\n"
        f"🗡 Контракт наёмника — {config.SHOP_HIRE_BLADE} "
        f"(+{int(config.SHOP_HIRE_BLADE_BONUS * 100)}% к одному рейду лидера)\n"
        f"🛡 Взнос в щит страны — {config.NATION_SHIELD_CONTRIB}\n\n"
        f"💰 {player.crowns}"
    )


def shop_catalog_prestige(player: Player) -> str:
    return (
        "👑 Престиж — зачем: казна, мастерство, азарт\n\n"
        f"🏛 Вклад в казну — {config.SHOP_TREASURY_GIFT}\n"
        f"🕯 Подношение трону — {config.SHOP_TRIBUTE} "
        f"(в казну + {int(config.SHOP_TRIBUTE_WORK_BONUS * 100)}% работы "
        f"на {config.SHOP_TRIBUTE_HOURS}ч)\n"
        f"📜 Лицензия мастерства — {config.SHOP_CRAFT_LICENSE} "
        f"(+{int(config.SHOP_CRAFT_LICENSE_BONUS * 100)}% к "
        f"{config.SHOP_CRAFT_LICENSE_STACKS} работам)\n"
        f"🎰 Колесо удачи — {config.SHOP_WHEEL_COST} "
        f"(кд {config.SHOP_WHEEL_COOLDOWN_SEC} сек; "
        f"выкуп трофеев −{int((1 - config.SHOP_WHEEL_SELL_MULT) * 100)}%)\n\n"
        f"💰 {player.crowns}"
    )


def shop_catalog_text(player: Player) -> str:
    """Совместимость: полный каталог."""
    return shop_root_text(player)


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


async def buy_tribute(session: AsyncSession, player: Player) -> dict:
    cost = int(config.SHOP_TRIBUTE)
    if not player.nation_id or not player.nation:
        raise ShopError("Нужна страна для подношения трону.")
    if player.crowns < cost:
        raise ShopError(f"Нужно {cost} крон (у тебя {player.crowns}).")
    player.crowns -= cost
    player.nation.treasury += cost
    hours = int(config.SHOP_TRIBUTE_HOURS)
    await set_buff(
        session,
        player.vk_id,
        "tribute_work",
        1,
        meta="tribute",
        expires_at=utcnow() + timedelta(hours=hours),
    )
    await session.commit()
    return {
        "cost": cost,
        "treasury": player.nation.treasury,
        "nation": f"{player.nation.flag_emoji} {player.nation.name}",
        "bonus_pct": int(config.SHOP_TRIBUTE_WORK_BONUS * 100),
        "hours": hours,
        "crowns": player.crowns,
    }


async def buy_craft_license(session: AsyncSession, player: Player) -> dict:
    cost = int(config.SHOP_CRAFT_LICENSE)
    if player.crowns < cost:
        raise ShopError(f"Нужно {cost} крон (у тебя {player.crowns}).")
    existing = await get_buff(session, player.vk_id, "craft_boost")
    if existing and existing.stacks >= int(config.SHOP_CRAFT_LICENSE_STACKS) * 2:
        raise ShopError("Слишком много лицензий — сначала отработай.")
    player.crowns -= cost
    stacks = int(config.SHOP_CRAFT_LICENSE_STACKS)
    if existing and existing.stacks > 0:
        stacks = existing.stacks + stacks
    await set_buff(session, player.vk_id, "craft_boost", stacks)
    await session.commit()
    return {
        "cost": cost,
        "stacks": stacks,
        "bonus_pct": int(config.SHOP_CRAFT_LICENSE_BONUS * 100),
        "crowns": player.crowns,
    }


async def buy_hire_blade(session: AsyncSession, player: Player) -> dict:
    cost = int(config.SHOP_HIRE_BLADE)
    if not player.nation_id:
        raise ShopError("Нужна страна.")
    if player.crowns < cost:
        raise ShopError(f"Нужно {cost} крон (у тебя {player.crowns}).")
    existing = await get_buff(session, player.vk_id, "hire_blade")
    if existing and existing.stacks > 0:
        raise ShopError("Контракт уже висит — сначала рейд (нужен лидер с контрактом).")
    player.crowns -= cost
    await set_buff(session, player.vk_id, "hire_blade", 1)
    await session.commit()
    return {
        "cost": cost,
        "bonus_pct": int(config.SHOP_HIRE_BLADE_BONUS * 100),
        "crowns": player.crowns,
    }


async def buy_wheel(
    session: AsyncSession,
    player: Player,
    cost: int | None = None,
) -> dict:
    """Колесо: отрицательный EV; трофеи bound — уценка только при выкупе у бота."""
    spin_cost = int(cost if cost is not None else config.SHOP_WHEEL_COST)
    cd = int(config.SHOP_WHEEL_COOLDOWN_SEC)
    last = ensure_aware(player.last_wheel_at)
    if last and cd > 0:
        left = cd - int((utcnow() - last).total_seconds())
        if left > 0:
            raise ShopError(f"Колесо остывает ещё {left} сек.")
    if player.crowns < spin_cost:
        raise ShopError(f"Нужно {spin_cost} крон (у тебя {player.crowns}).")
    player.crowns -= spin_cost
    player.last_wheel_at = utcnow()

    reward_type = random.choices(
        ("empty", "crowns", "item"), weights=(15, 50, 35), k=1
    )[0]

    if reward_type == "empty":
        await session.commit()
        return {
            "cost": spin_cost,
            "type": "empty",
            "crowns": player.crowns,
        }

    if reward_type == "crowns":
        amount = random.choices(
            (15, 30, 45, 80, 150), weights=(32, 30, 22, 12, 4), k=1
        )[0]
        player.crowns += amount
        await session.commit()
        return {
            "cost": spin_cost,
            "type": "crowns",
            "amount": amount,
            "crowns": player.crowns,
        }

    items = cat.all_items()
    weights = [
        config.WHEEL_RARITY_WEIGHTS.get(item["rarity"], 0.0) for item in items
    ]
    if sum(weights) <= 0:
        weights = [1.0] * len(items)
    item = random.choices(items, weights=weights, k=1)[0]
    await add_item(session, player, item["id"], bound=True)
    return {
        "cost": spin_cost,
        "type": "item",
        "item": item,
        "crowns": player.crowns,
        "bound": True,
    }
