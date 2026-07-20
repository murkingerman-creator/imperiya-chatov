"""Броски дропа предметов."""

from __future__ import annotations

import random

from sqlalchemy.ext.asyncio import AsyncSession

from bot import config
from content import items_catalog as cat
from db.models import Player
from services.inventory import add_item


def _weighted_rarity(
    weights: dict[str, float],
    rng: random.Random | None = None,
) -> str:
    rng = rng or random
    keys = list(weights.keys())
    vals = [float(weights[k]) for k in keys]
    if sum(vals) <= 0:
        keys = list(config.LOOT_RARITY_WEIGHTS.keys())
        vals = [float(config.LOOT_RARITY_WEIGHTS[k]) for k in keys]
    return rng.choices(keys, weights=vals, k=1)[0]


def roll_drop(
    pool: str,
    *,
    success: bool = True,
    job: str | None = None,
    event_key: str | None = None,
    loot_luck: float = 0.0,
    loot_mult: float = 1.0,
    force: bool = False,
    rarity_weights: dict[str, float] | None = None,
    rng: random.Random | None = None,
) -> dict | None:
    """Вернуть item dict или None. Не пишет в БД."""
    rng = rng or random
    weights = rarity_weights or dict(config.LOOT_RARITY_WEIGHTS)

    if pool == "smuggle":
        chance = config.LOOT_SMUGGLE_SUCCESS if success else config.LOOT_CHANCE_FAIL
    elif pool == "raid":
        chance = config.LOOT_RAID_CHANCE
    else:
        chance = config.LOOT_CHANCE_SUCCESS if success else config.LOOT_CHANCE_FAIL
        if success and job == "guard":
            chance += config.LOOT_GUARD_SUCCESS_BONUS

    if event_key == "gold_vein":
        chance *= 1.4
    elif event_key == "plague":
        chance *= 0.7

    chance *= max(0.1, float(loot_mult or 1.0))
    chance = min(0.55, chance + loot_luck)

    if not force and rng.random() > chance:
        return None

    # plague: allow cursed pool items into mix
    pools = [pool]
    if event_key == "plague" and pool != "raid":
        pools.append("cursed")

    for _ in range(8):
        rarity = _weighted_rarity(weights, rng)
        candidates = []
        for p in pools:
            candidates.extend(cat.items_in_pool(p, rarity))
        # dedupe by id
        seen = set()
        uniq = []
        for c in candidates:
            if c["id"] not in seen:
                seen.add(c["id"])
                uniq.append(c)
        if uniq:
            return rng.choice(uniq)
        # fallback lower rarity
    # any from pool
    any_items = []
    for p in pools:
        any_items.extend(cat.items_in_pool(p))
    if not any_items:
        any_items = cat.all_items()
    return rng.choice(any_items) if any_items else None


async def grant_drop(
    session: AsyncSession,
    player: Player,
    pool: str,
    *,
    success: bool = True,
    job: str | None = None,
    event_key: str | None = None,
    loot_luck: float = 0.0,
    loot_mult: float = 1.0,
    force_item: dict | None = None,
) -> dict | None:
    from services.loot_settings import get_loot_weights

    rarity_weights, _src = await get_loot_weights(session)
    item = force_item or roll_drop(
        pool,
        success=success,
        job=job,
        event_key=event_key,
        loot_luck=loot_luck,
        loot_mult=loot_mult,
        rarity_weights=rarity_weights,
    )
    if not item:
        return None
    result = await add_item(session, player, item["id"], 1)
    rarity = item.get("rarity") or ""
    if rarity in ("epic", "legendary", "mythic"):
        from services.chronicle_store import add_event

        mark = cat.RARITY_MARK.get(rarity, "✨")
        label = cat.RARITY_LABEL.get(rarity, rarity)
        who = player.name or f"Игрок {player.vk_id}"
        await add_event(
            session,
            "loot",
            f"{mark} {who} добыл [{label}] {item['name']}",
            str(player.nation_id or ""),
        )
    return {
        "item": result["item"],
        "first": result["first"],
        "titles": result["titles"],
        "text": cat.format_item(result["item"]),
    }
