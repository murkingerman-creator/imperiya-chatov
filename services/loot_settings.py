"""Runtime-настройки весов редкости лута и колеса (MetaKV)."""

from __future__ import annotations

import json
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from bot import config
from services.chronicle_store import get_meta, set_meta

logger = logging.getLogger("empire.loot_settings")

KEY_LOOT = "loot_rarity_weights"
KEY_WHEEL = "wheel_rarity_weights"

RARITIES = ("common", "uncommon", "rare", "epic", "legendary", "mythic")

# потолки, чтобы админ случайно не сломал экономику
LOOT_CAPS = {
    "common": 200.0,
    "uncommon": 100.0,
    "rare": 40.0,
    "epic": 15.0,
    "legendary": 8.0,
    "mythic": 3.0,
}
WHEEL_CAPS = {
    "common": 200.0,
    "uncommon": 80.0,
    "rare": 20.0,
    "epic": 5.0,
    "legendary": 2.0,
    "mythic": 1.0,
}


class LootSettingsError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def _defaults_loot() -> dict[str, float]:
    return {k: float(v) for k, v in config.LOOT_RARITY_WEIGHTS.items()}


def _defaults_wheel() -> dict[str, float]:
    return {k: float(v) for k, v in config.WHEEL_RARITY_WEIGHTS.items()}


def _parse_json(raw: str, defaults: dict[str, float]) -> dict[str, float]:
    if not raw or not raw.strip():
        return dict(defaults)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return dict(defaults)
    out = dict(defaults)
    for k in RARITIES:
        if k in data:
            try:
                out[k] = float(data[k])
            except (TypeError, ValueError):
                pass
    return out


def _validate(weights: dict[str, float], caps: dict[str, float]) -> dict[str, float]:
    out: dict[str, float] = {}
    for k in RARITIES:
        v = float(weights.get(k, 0.0))
        if v < 0:
            raise LootSettingsError(f"{k}: вес не может быть < 0")
        cap = caps.get(k, 200.0)
        if v > cap:
            raise LootSettingsError(f"{k}: максимум {cap}")
        out[k] = v
    if sum(out.values()) <= 0:
        raise LootSettingsError("Нужен хотя бы один вес > 0")
    return out


def parse_weights_args(text: str) -> dict[str, float]:
    """'common=70 uncommon=20' или 'common:70'."""
    parts = text.replace(",", " ").split()
    out: dict[str, float] = {}
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if "=" in part:
            k, _, v = part.partition("=")
        elif ":" in part:
            k, _, v = part.partition(":")
        else:
            raise LootSettingsError(f"Не понял «{part}». Формат: common=70")
        k = k.strip().lower()
        if k not in RARITIES:
            raise LootSettingsError(
                f"Неизвестная редкость «{k}». "
                f"Доступно: {', '.join(RARITIES)}"
            )
        try:
            out[k] = float(v.strip().replace(",", "."))
        except ValueError as e:
            raise LootSettingsError(f"{k}: не число «{v}»") from e
    if not out:
        raise LootSettingsError("Укажи хотя бы один вес, напр. common=70")
    return out


def format_weights(weights: dict[str, float], *, title: str, source: str) -> str:
    total = sum(weights.values()) or 1.0
    lines = [f"{title} ({source})", ""]
    for k in RARITIES:
        w = float(weights.get(k, 0.0))
        pct = 100.0 * w / total
        lines.append(f"• {k}: {w:g} (~{pct:.1f}%)")
    lines.append("")
    lines.append(
        "Смена: !лут common=70 uncommon=20 …\n"
        "Колесо: !колесо common=82 …\n"
        "Сброс: !лут сброс · !колесо сброс"
    )
    return "\n".join(lines)


async def get_loot_weights(session: AsyncSession) -> tuple[dict[str, float], str]:
    raw = await get_meta(session, KEY_LOOT, "")
    defaults = _defaults_loot()
    if not raw:
        return defaults, "дефолт config"
    return _parse_json(raw, defaults), "override БД"


async def get_wheel_weights(session: AsyncSession) -> tuple[dict[str, float], str]:
    raw = await get_meta(session, KEY_WHEEL, "")
    defaults = _defaults_wheel()
    if not raw:
        return defaults, "дефолт config"
    return _parse_json(raw, defaults), "override БД"


async def set_loot_weights(
    session: AsyncSession, partial: dict[str, float], *, admin_id: int
) -> dict[str, float]:
    current, _ = await get_loot_weights(session)
    merged = {**current, **partial}
    validated = _validate(merged, LOOT_CAPS)
    await set_meta(session, KEY_LOOT, json.dumps(validated, ensure_ascii=False))
    logger.info("loot weights by %s: %s", admin_id, validated)
    return validated


async def set_wheel_weights(
    session: AsyncSession, partial: dict[str, float], *, admin_id: int
) -> dict[str, float]:
    current, _ = await get_wheel_weights(session)
    merged = {**current, **partial}
    validated = _validate(merged, WHEEL_CAPS)
    await set_meta(session, KEY_WHEEL, json.dumps(validated, ensure_ascii=False))
    logger.info("wheel weights by %s: %s", admin_id, validated)
    return validated


async def reset_loot_weights(session: AsyncSession, *, admin_id: int) -> dict[str, float]:
    await set_meta(session, KEY_LOOT, "")
    logger.info("loot weights reset by %s", admin_id)
    return _defaults_loot()


async def reset_wheel_weights(session: AsyncSession, *, admin_id: int) -> dict[str, float]:
    await set_meta(session, KEY_WHEEL, "")
    logger.info("wheel weights reset by %s", admin_id)
    return _defaults_wheel()
