"""Заказы дня по работам (МСК)."""

from __future__ import annotations

import json
import random
from datetime import timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from bot import config
from db.models import Player
from services.chronicle_store import get_meta, set_meta
from services.levels import add_xp
from services.player import utcnow

MSK = timezone(timedelta(hours=3))
META_ORDERS = "daily_work_orders"
META_ORDERS_DATE = "daily_orders_date"

ORDER_POOL = (
    ("mine", 2),
    ("market", 2),
    ("fish", 3),
    ("farm", 2),
    ("forge", 2),
    ("tavern", 3),
    ("guard", 2),
    ("stable", 2),
)


def _today_msk() -> str:
    return utcnow().astimezone(MSK).strftime("%Y-%m-%d")


def parse_progress(raw: str | None) -> dict[int, int]:
    out: dict[int, int] = {}
    for part in (raw or "").split(","):
        part = part.strip()
        if ":" not in part:
            continue
        k, _, v = part.partition(":")
        try:
            out[int(k)] = int(v)
        except ValueError:
            continue
    return out


def dump_progress(prog: dict[int, int]) -> str:
    return ",".join(f"{k}:{v}" for k, v in sorted(prog.items()) if v > 0)[:250]


async def ensure_daily_orders(session: AsyncSession) -> list[dict]:
    today = _today_msk()
    stored = await get_meta(session, META_ORDERS_DATE)
    raw = await get_meta(session, META_ORDERS)
    if stored == today and raw:
        try:
            data = json.loads(raw)
            if isinstance(data, list) and data:
                return data
        except json.JSONDecodeError:
            pass

    picks = random.sample(ORDER_POOL, k=min(3, len(ORDER_POOL)))
    orders = [{"job": j, "need": n, "idx": i} for i, (j, n) in enumerate(picks)]
    await set_meta(session, META_ORDERS, json.dumps(orders, ensure_ascii=False))
    await set_meta(session, META_ORDERS_DATE, today)
    await session.commit()
    return orders


async def get_orders_view(session: AsyncSession, player: Player) -> str:
    orders = await ensure_daily_orders(session)
    prog = parse_progress(getattr(player, "order_progress", None) or "")
    # сброс прогресса при новом дне
    day = _today_msk()
    if (getattr(player, "order_progress", None) or "").startswith("d:"):
        stored_day = player.order_progress[2:].split("|", 1)[0]
        raw_prog = (
            player.order_progress.split("|", 1)[1]
            if "|" in player.order_progress
            else ""
        )
        if stored_day != day:
            prog = {}
            player.order_progress = f"d:{day}|"
            await session.commit()
        else:
            prog = parse_progress(raw_prog)
    else:
        player.order_progress = f"d:{day}|" + dump_progress(prog)
        await session.commit()

    lines = ["📋 Заказы дня (МСК):"]
    for o in orders:
        idx = int(o["idx"])
        need = int(o["need"])
        cur = min(need, int(prog.get(idx, 0)))
        done = cur >= need or bool(prog.get(100 + idx))
        title = config.JOBS.get(o["job"], {}).get("title", o["job"])
        mark = "✅" if done else "▫️"
        lines.append(f"{mark} {title}: {cur}/{need}")
    lines.append(
        f"\nНаграда за каждый заказ: {config.WORK_ORDER_REWARD}🪙 "
        f"+ {config.WORK_ORDER_XP} XP (авто при выполнении)."
    )
    return "\n".join(lines)


def _prog_day_and_map(player: Player) -> tuple[str, dict[int, int]]:
    day = _today_msk()
    raw = getattr(player, "order_progress", None) or ""
    if raw.startswith("d:") and "|" in raw:
        stored, _, rest = raw[2:].partition("|")
        if stored == day:
            return day, parse_progress(rest)
        return day, {}
    return day, {}


async def on_job_for_orders(
    session: AsyncSession, player: Player, job: str
) -> str | None:
    orders = await ensure_daily_orders(session)
    day, prog = _prog_day_and_map(player)
    notes: list[str] = []
    changed = False
    for o in orders:
        if o["job"] != job:
            continue
        idx = int(o["idx"])
        need = int(o["need"])
        claim_key = 100 + idx  # 1 = уже выплачено
        if prog.get(claim_key):
            continue
        cur = int(prog.get(idx, 0))
        if cur >= need:
            continue
        cur += 1
        prog[idx] = cur
        changed = True
        if cur >= need:
            prog[claim_key] = 1
            player.crowns += int(config.WORK_ORDER_REWARD)
            xp = await add_xp(
                session, player, int(config.WORK_ORDER_XP), reason="заказ дня"
            )
            title = config.JOBS.get(job, {}).get("title", job)
            notes.append(
                f"📋 Заказ выполнен ({title}): "
                f"+{config.WORK_ORDER_REWARD}🪙 +{config.WORK_ORDER_XP} XP"
            )
            if xp.get("level_ups"):
                notes.extend(xp["level_ups"])

    if changed:
        player.order_progress = f"d:{day}|" + dump_progress(prog)
        await session.commit()
    return "\n".join(notes) if notes else None
