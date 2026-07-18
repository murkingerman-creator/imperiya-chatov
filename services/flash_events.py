"""Случайные вспышки судьбы: автораз в 2–3ч + админский форс."""

from __future__ import annotations

import json
import logging
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from bot import config
from content.flash_events import FLASH_EVENTS, get_flash_def
from services.chronicle_store import get_meta, set_meta
from services.player import utcnow

logger = logging.getLogger("empire.flash")

META_FLASH = "flash_event"
META_NEXT = "flash_event_next_at"


def _parse_ends(raw_ends: str) -> datetime | None:
    try:
        ends_dt = datetime.fromisoformat(raw_ends)
    except (TypeError, ValueError):
        return None
    if ends_dt.tzinfo is None:
        ends_dt = ends_dt.replace(tzinfo=timezone.utc)
    return ends_dt


async def get_flash_event(session: AsyncSession) -> dict | None:
    raw = await get_meta(session, META_FLASH)
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    ends = _parse_ends(data.get("ends_at") or "")
    if not ends or utcnow() >= ends:
        return None
    key = data.get("key")
    base = get_flash_def(key) if key else None
    if not base:
        return None
    return {**base, "key": key, "ends_at": ends, "forced": bool(data.get("forced"))}


def format_flash_event(ev: dict | None) -> str:
    if not ev:
        return "⚡ Вспышка судьбы: сейчас тихо"
    left = ""
    ends = ev.get("ends_at")
    if isinstance(ends, datetime):
        mins = max(0, int((ends - utcnow()).total_seconds() / 60))
        left = f"\n⏳ Ещё ~{mins // 60}ч {mins % 60}м"
    buffs = ev.get("buffs") or "—"
    debuffs = ev.get("debuffs") or "—"
    return (
        f"⚡ Вспышка судьбы\n"
        f"━━━━━━━━━━━━━━\n"
        f"{ev['title']}\n"
        f"{ev['desc']}\n\n"
        f"✅ Бафы: {buffs}\n"
        f"⚠ Дебафы: {debuffs}"
        f"{left}"
    )


def format_flash_announce(ev: dict) -> str:
    hours = ev.get("hours")
    dur = ""
    if hours is not None:
        dur = f"\nДлительность: ~{float(hours):.1f} ч."
    elif isinstance(ev.get("ends_at"), datetime):
        mins = max(0, int((ev["ends_at"] - utcnow()).total_seconds() / 60))
        dur = f"\nДлительность: ~{mins // 60}ч {mins % 60}м"
    return (
        f"⚡ Вспышка судьбы!\n"
        f"━━━━━━━━━━━━━━\n"
        f"{ev['title']}\n"
        f"{ev['desc']}\n\n"
        f"✅ Бафы: {ev.get('buffs') or '—'}\n"
        f"⚠ Дебафы: {ev.get('debuffs') or '—'}"
        f"{dur}\n\n"
        f"Смотри «🌤 Ивент дня» — вспышка суммируется с ивентом суток."
    )


async def _schedule_next(session: AsyncSession) -> datetime:
    lo = float(config.FLASH_INTERVAL_MIN_HOURS)
    hi = float(config.FLASH_INTERVAL_MAX_HOURS)
    hours = random.uniform(lo, hi)
    nxt = utcnow() + timedelta(hours=hours)
    await set_meta(session, META_NEXT, nxt.isoformat())
    return nxt


async def force_flash(
    session: AsyncSession,
    key: str | None = None,
    hours: float | None = None,
    *,
    forced: bool = True,
) -> dict:
    """Запустить вспышку (случайную или по ключу)."""
    if key is None:
        key = random.choice(list(FLASH_EVENTS.keys()))
    if key not in FLASH_EVENTS:
        raise ValueError(f"Неизвестная вспышка: {key}")
    h = hours if hours is not None else float(config.FLASH_DURATION_HOURS)
    h = max(0.25, min(float(config.FLASH_DURATION_MAX_HOURS), float(h)))
    ends = utcnow() + timedelta(hours=h)
    payload = {
        "key": key,
        "ends_at": ends.isoformat(),
        "forced": forced,
    }
    await set_meta(session, META_FLASH, json.dumps(payload, ensure_ascii=False))
    await _schedule_next(session)
    base = FLASH_EVENTS[key]
    return {**base, "key": key, "ends_at": ends, "hours": h, "forced": forced}


async def clear_flash(session: AsyncSession) -> dict | None:
    prev = await get_flash_event(session)
    await set_meta(session, META_FLASH, "")
    return prev


async def maybe_roll_flash(session: AsyncSession) -> dict | None:
    """
    Авторолл раз в 2–3 часа.
    Возвращает новую вспышку, если сработало; иначе None.
    """
    now = utcnow()
    raw_next = await get_meta(session, META_NEXT)
    if not raw_next:
        await _schedule_next(session)
        return None
    try:
        nxt = datetime.fromisoformat(raw_next)
        if nxt.tzinfo is None:
            nxt = nxt.replace(tzinfo=timezone.utc)
    except ValueError:
        await _schedule_next(session)
        return None

    if now < nxt:
        return None

    ev = await force_flash(session, key=None, hours=None, forced=False)
    logger.info("flash rolled: %s until %s", ev["key"], ev["ends_at"])
    return ev


def list_flashes_text() -> str:
    lines = ["⚡ Вспышки судьбы (ключи для !вспышка KEY):", ""]
    for key, ev in FLASH_EVENTS.items():
        lines.append(f"• {key} — {ev['title']}")
        lines.append(f"  ✅ {ev['buffs']} · ⚠ {ev['debuffs']}")
    return "\n".join(lines)
