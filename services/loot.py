"""Броски дропа предметов."""

from __future__ import annotations

import random

from sqlalchemy.ext.asyncio import AsyncSession

from bot import config
from content import items_catalog as cat
from db.models import Player
from services.inventory import add_item


def _weighted_rarity(rng: random.Random | None = None) -> str:
    rng = rng or random
    weights = config.LOOT_RARITY_WEIGHTS
    keys = list(weights.keys())
    vals = [weights[k] for k in keys]
    return rng.choices(keys, weights=vals, k=1)[0]


def roll_drop(
    pool: str,
    *,
    success: bool = True,
    job: str | None = None,
    event_key: str | None = None,
    loot_luck: float = 0.0,
    force: bool = False,
    rng: random.Random | None = None,
) -> dict | None:
    """Вернуть item dict или None. Не пишет в БД."""
    rng = rng or random

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

    chance = min(0.55, chance + loot_luck)

    if not force and rng.random() > chance:
        return None

    # plague: allow cursed pool items into mix
    pools = [pool]
    if event_key == "plague" and pool != "raid":
        pools.append("cursed")

    for _ in range(8):
        rarity = _weighted_rarity(rng)
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
    force_item: dict | None = None,
) -> dict | None:
    item = force_item or roll_drop(
        pool,
        success=success,
        job=job,
        event_key=event_key,
        loot_luck=loot_luck,
    )
    if not item:
        return None
    result = await add_item(session, player, item["id"], 1)
    return {
        "item": result["item"],
        "first": result["first"],
        "titles": result["titles"],
        "text": cat.format_item(result["item"]),
    }
