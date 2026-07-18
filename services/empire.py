"""Империя сезона: глобальный указ-бафф после победы."""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from bot import config
from db.models import Nation
from services.chronicle_store import get_meta, set_meta
from services.nation import get_nation_by_id
from services.player import ensure_aware, utcnow


async def start_empire_decree(session: AsyncSession, nation: Nation) -> datetime:
    until = utcnow() + timedelta(days=config.EMPIRE_DECREE_DAYS)
    await set_meta(session, "empire_nation_id", str(nation.id))
    await set_meta(session, "empire_until", until.isoformat())
    await set_meta(session, "empire_name", f"{nation.flag_emoji} {nation.name}")
    return until


async def get_empire_status(session: AsyncSession) -> dict | None:
    until_raw = await get_meta(session, "empire_until")
    if not until_raw:
        return None
    try:
        until = datetime.fromisoformat(until_raw)
    except ValueError:
        return None
    until = ensure_aware(until)
    if not until or until <= utcnow():
        return None
    nid_raw = await get_meta(session, "empire_nation_id")
    name = await get_meta(session, "empire_name") or "Империя"
    nation = None
    if nid_raw and nid_raw.isdigit():
        nation = await get_nation_by_id(session, int(nid_raw))
    return {
        "until": until,
        "nation": nation,
        "name": name
        if not nation
        else f"{nation.flag_emoji} {nation.name}",
        "work_mult": config.EMPIRE_WORK_MULT,
        "loot_luck": config.EMPIRE_LOOT_LUCK,
    }


def format_empire_line(status: dict | None) -> str:
    if not status:
        return ""
    left_h = max(1, int((status["until"] - utcnow()).total_seconds() / 3600))
    return (
        f"🏛 Указ Империи ({status['name']}): "
        f"+{int(status['work_mult'] * 100)}% работы, "
        f"+{int(status['loot_luck'] * 100)}% удача лута · ещё ~{left_h}ч"
    )
