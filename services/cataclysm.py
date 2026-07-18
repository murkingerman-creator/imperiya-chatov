"""Редкие катаклизмы на сутки."""

from __future__ import annotations

import json
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from bot import config
from services.chronicle_store import add_event, get_meta, set_meta
from services.player import utcnow


async def get_cataclysm(session: AsyncSession) -> dict | None:
    raw = await get_meta(session, "cataclysm")
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    ends = data.get("ends_at")
    if not ends:
        return None
    ends_dt = datetime.fromisoformat(ends)
    if ends_dt.tzinfo is None:
        ends_dt = ends_dt.replace(tzinfo=timezone.utc)
    if utcnow() >= ends_dt:
        return None
    key = data.get("key")
    spec = config.CATACLYSMS.get(key or "")
    if not spec:
        return None
    return {**spec, "key": key, "ends_at": ends_dt}


async def force_cataclysm(
    session: AsyncSession, key: str | None = None, hours: float | None = None
) -> dict:
    key = key or random.choice(list(config.CATACLYSMS))
    if key not in config.CATACLYSMS:
        raise ValueError(f"Неизвестный катаклизм: {key}")
    h = hours if hours is not None else float(config.CATACLYSM_HOURS)
    h = max(1.0, min(48.0, float(h)))
    ends = utcnow() + timedelta(hours=h)
    payload = {"key": key, "ends_at": ends.isoformat()}
    await set_meta(session, "cataclysm", json.dumps(payload, ensure_ascii=False))
    spec = config.CATACLYSMS[key]
    await add_event(session, "mythic", f"🌪 {spec['title']}: {spec['chronicle']}", "")
    return {**spec, "key": key, "ends_at": ends}


async def clear_cataclysm(session: AsyncSession) -> None:
    await set_meta(session, "cataclysm", "")


async def maybe_roll_cataclysm(session: AsyncSession) -> dict | None:
    if await get_cataclysm(session):
        return None
    # не чаще раза в ~5 дней
    last = await get_meta(session, "cataclysm_last_day")
    today = utcnow().strftime("%Y-%m-%d")
    if last:
        try:
            from datetime import date

            d0 = date.fromisoformat(last)
            d1 = date.fromisoformat(today)
            if (d1 - d0).days < 5:
                return None
        except ValueError:
            pass
    if random.random() > float(config.CATACLYSM_CHANCE_PER_TICK):
        return None
    ev = await force_cataclysm(session)
    await set_meta(session, "cataclysm_last_day", today)
    return ev


def format_cataclysm(ev: dict | None) -> str:
    if not ev:
        return ""
    left = max(1, int((ev["ends_at"] - utcnow()).total_seconds() / 3600))
    return f"🌪 {ev['title']}: {ev['desc']} · ещё ~{left}ч"


def cataclysm_work_mult(ev: dict | None) -> float:
    return float(ev.get("work_mult", 1.0)) if ev else 1.0


def cataclysm_loot_mult(ev: dict | None) -> float:
    return float(ev.get("loot_mult", 1.0)) if ev else 1.0


def cataclysm_raid_mult(ev: dict | None) -> float:
    return float(ev.get("raid_mult", 1.0)) if ev else 1.0
