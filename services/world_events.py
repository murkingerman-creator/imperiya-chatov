import json
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from bot import config
from services.chronicle_store import get_meta, set_meta
from services.player import utcnow

MSK = timezone(timedelta(hours=3))


def _today_key() -> str:
    return utcnow().astimezone(MSK).strftime("%Y-%m-%d")


async def get_active_event(session: AsyncSession) -> dict | None:
    raw = await get_meta(session, "world_event")
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
    if key not in config.WORLD_EVENTS:
        return None
    return {**config.WORLD_EVENTS[key], "key": key, "ends_at": ends_dt}


async def ensure_daily_event(session: AsyncSession) -> dict:
    """Ротация ивента раз в сутки (или ночь рейдов по пятницам)."""
    today = _today_key()
    last_day = await get_meta(session, "world_event_day")
    active = await get_active_event(session)
    if last_day == today and active:
        return active

    weekday = utcnow().astimezone(MSK).weekday()  # 0=Mon ... 4=Fri
    if weekday == 4:  # пятница — ночь рейдов
        key = "raid_night"
    else:
        pool = [k for k in config.WORLD_EVENTS if k != "raid_night"]
        key = random.choice(pool)

    ends = utcnow() + timedelta(hours=24)
    payload = {"key": key, "ends_at": ends.isoformat()}
    await set_meta(session, "world_event", json.dumps(payload, ensure_ascii=False))
    await set_meta(session, "world_event_day", today)
    ev = {**config.WORLD_EVENTS[key], "key": key, "ends_at": ends}
    return ev


def format_event(ev: dict | None) -> str:
    if not ev:
        return "🌤 Ивент дня: обычный день"
    left = ""
    ends = ev.get("ends_at")
    if isinstance(ends, datetime):
        mins = max(0, int((ends - utcnow()).total_seconds() / 60))
        left = f" · ещё ~{mins // 60}ч {mins % 60}м"
    return f"{ev['title']}: {ev['desc']}{left}"


def work_multiplier(ev: dict | None) -> float:
    return float(ev["work_mult"]) if ev else 1.0


def tax_modifier(ev: dict | None) -> float:
    return float(ev.get("tax_add") or 0) if ev else 0.0


def raid_multiplier(ev: dict | None) -> float:
    return float(ev["raid_mult"]) if ev else 1.0


def raid_cooldown(ev: dict | None) -> timedelta:
    if ev and ev.get("raid_night"):
        return timedelta(minutes=config.RAID_NIGHT_COOLDOWN_MINUTES)
    hours = config.RAID_COOLDOWN_HOURS
    if ev:
        hours = hours * float(ev.get("raid_cd_mult") or 1.0)
    return timedelta(hours=hours)
