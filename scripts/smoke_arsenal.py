"""Smoke checks for Arsenal (loot / caps / catalog)."""

from __future__ import annotations

import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from bot import config
from data import items_catalog as cat
from services.item_effects import Loadout, apply_raid_modifiers, apply_work_modifiers
from services.loot import roll_drop


def main() -> None:
    n = cat.catalog_size()
    assert n >= 90, f"catalog too small: {n}"
    print(f"catalog OK: {n} items")

    rng = random.Random(42)
    drops = [roll_drop("mine", success=True, job="mine", force=True, rng=rng) for _ in range(20)]
    assert all(d is not None for d in drops)
    print("force drop OK")

    # rarity weights produce variety over many rolls
    rng2 = random.Random(1)
    rarities = set()
    for _ in range(500):
        d = roll_drop("mine", success=True, job="mine", force=True, rng=rng2)
        rarities.add(d["rarity"])
    assert "common" in rarities and "uncommon" in rarities
    print(f"rarity variety OK: {sorted(rarities)}")

    lo = Loadout(work_mult=0.50, job_bonus={"mine": 0.20}, raid_mult=0.40)
    lo.work_mult = min(config.WORK_MULT_CAP, lo.work_mult)
    lo.raid_mult = min(config.RAID_MULT_CAP, lo.raid_mult)
    gross, wmult = apply_work_modifiers(100, lo, "mine")
    stolen, rmult = apply_raid_modifiers(100, lo)
    assert wmult <= 1.0 + config.WORK_MULT_CAP + 0.16, wmult
    assert rmult <= 1.0 + config.RAID_MULT_CAP + 0.01, rmult
    print(f"caps OK: work_mult={wmult:.2f} raid_mult={rmult:.2f} gross={gross} stolen={stolen}")

    myths = [i for i in cat.all_items() if i["rarity"] == "mythic"]
    legs = [i for i in cat.all_items() if i["rarity"] == "legendary"]
    assert len(myths) >= 5 and len(legs) >= 10
    assert all(m.get("aura") or m.get("charge") for m in myths)
    print(f"legendaries={len(legs)} mythics={len(myths)} OK")
    print("ALL SMOKE PASSED")


if __name__ == "__main__":
    main()
