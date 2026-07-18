"""Районы столицы: рынок, казарма, храм."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from bot import config
from services.roles import can_treasury
from db.models import Nation, Player


class DistrictError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


DISTRICT_META = {
    "market": {
        "name": "Рынок",
        "emoji": "🛒",
        "field": "district_market",
        "effect": "работы",
        "bonuses": config.DISTRICT_MARKET_WORK,
    },
    "barracks": {
        "name": "Казарма",
        "emoji": "⚔",
        "field": "district_barracks",
        "effect": "рейд",
        "bonuses": config.DISTRICT_BARRACKS_RAID,
    },
    "temple": {
        "name": "Храм",
        "emoji": "🛕",
        "field": "district_temple",
        "effect": "удача лута",
        "bonuses": config.DISTRICT_TEMPLE_LUCK,
    },
}


def _level(nation: Nation, key: str) -> int:
    meta = DISTRICT_META[key]
    return max(0, min(config.DISTRICT_MAX_LEVEL, int(getattr(nation, meta["field"], 0) or 0)))


def market_work_bonus(nation: Nation | None) -> float:
    if not nation:
        return 0.0
    return float(config.DISTRICT_MARKET_WORK[_level(nation, "market")])


def barracks_raid_bonus(nation: Nation | None) -> float:
    if not nation:
        return 0.0
    return float(config.DISTRICT_BARRACKS_RAID[_level(nation, "barracks")])


def temple_luck_bonus(nation: Nation | None) -> float:
    if not nation:
        return 0.0
    return float(config.DISTRICT_TEMPLE_LUCK[_level(nation, "temple")])


def districts_card_line(nation: Nation) -> str:
    parts = []
    for key, meta in DISTRICT_META.items():
        lv = _level(nation, key)
        bonus = meta["bonuses"][lv]
        parts.append(
            f"{meta['emoji']}{meta['name']} {lv}/{config.DISTRICT_MAX_LEVEL}"
            + (f" (+{int(bonus * 100)}%)" if lv else "")
        )
    return "🏙 " + " · ".join(parts)


def districts_status_text(nation: Nation) -> str:
    lines = [
        f"🏙 Районы столицы — {nation.flag_emoji} {nation.name}",
        f"Казна: {nation.treasury}",
        "",
    ]
    for key, meta in DISTRICT_META.items():
        lv = _level(nation, key)
        bonus = meta["bonuses"][lv]
        lines.append(
            f"{meta['emoji']} {meta['name']}: ур. {lv}/{config.DISTRICT_MAX_LEVEL}"
        )
        if lv:
            lines.append(f"   сейчас: +{int(bonus * 100)}% {meta['effect']}")
        if lv < config.DISTRICT_MAX_LEVEL:
            cost = config.DISTRICT_UPGRADE_COSTS[lv + 1]
            nxt = meta["bonuses"][lv + 1]
            lines.append(
                f"   апгрейд → ур.{lv + 1}: {cost}💰 "
                f"(+{int(nxt * 100)}% {meta['effect']})"
            )
        else:
            lines.append("   максимум")
        lines.append("")
    lines.append("Лидер/казначей: кнопки ниже или «район рынок|казарма|храм».")
    return "\n".join(lines)


async def upgrade_district(
    session: AsyncSession, player: Player, key: str
) -> dict:
    if key not in DISTRICT_META:
        raise DistrictError("Районы: рынок, казарма или храм.")
    if not player.nation_id or not player.nation:
        raise DistrictError("Нужна страна.")
    nation = player.nation

    if not await can_treasury(session, player):
        raise DistrictError("Апгрейд районов — лидер или казначей.")

    meta = DISTRICT_META[key]
    lv = _level(nation, key)
    if lv >= config.DISTRICT_MAX_LEVEL:
        raise DistrictError(f"{meta['name']} уже максимального уровня.")
    cost = int(config.DISTRICT_UPGRADE_COSTS[lv + 1])
    if nation.treasury < cost:
        raise DistrictError(f"Нужно {cost} из казны (есть {nation.treasury}).")
    nation.treasury -= cost
    setattr(nation, meta["field"], lv + 1)
    await session.commit()
    return {
        "nation": nation,
        "key": key,
        "name": meta["name"],
        "level": lv + 1,
        "cost": cost,
        "bonus": meta["bonuses"][lv + 1],
        "effect": meta["effect"],
    }
