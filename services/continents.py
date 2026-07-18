"""Континенты / великая война недели."""

from __future__ import annotations

import json
from datetime import timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot import config
from db.models import Nation
from services.achievements import grant_title
from services.chronicle_store import add_event, get_meta, set_meta
from services.player import utcnow

MSK = timezone(timedelta(hours=3))

BLOCS = ("north", "south", "center")


def assign_continent(nation_id: int) -> str:
    return BLOCS[(max(1, nation_id) - 1) % 3]


def continent_label(key: str) -> str:
    return config.CONTINENTS.get(key, key)


def week_id() -> str:
    return utcnow().astimezone(MSK).strftime("%Y-W%W")


async def _scores(session: AsyncSession) -> dict[str, int]:
    raw = await get_meta(session, f"continent_scores:{week_id()}")
    if not raw:
        return {b: 0 for b in BLOCS}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {b: 0 for b in BLOCS}
    return {b: int(data.get(b, 0)) for b in BLOCS}


async def _save_scores(session: AsyncSession, scores: dict[str, int]) -> None:
    await set_meta(
        session,
        f"continent_scores:{week_id()}",
        json.dumps(scores, ensure_ascii=False),
    )


async def add_continent_points(
    session: AsyncSession, attacker: Nation, defender: Nation, points: int
) -> None:
    a = attacker.continent or assign_continent(attacker.id)
    d = defender.continent or assign_continent(defender.id)
    if a == d:
        return
    scores = await _scores(session)
    scores[a] = scores.get(a, 0) + points
    await _save_scores(session, scores)


async def status_text(session: AsyncSession) -> str:
    scores = await _scores(session)
    lines = [f"🗺 Великая война · неделя {week_id()}", "Очки за рейды на чужой блок:"]
    for b in BLOCS:
        lines.append(f"• {continent_label(b)}: {scores.get(b, 0)}")
    buff = await get_continent_buff(session)
    if buff:
        lines.append("")
        lines.append(
            f"🏛 Бафф победителей ({continent_label(buff['bloc'])}): "
            f"+{int(buff['work_mult'] * 100)}% работы"
        )
    lines.append("")
    lines.append("Страны: Север / Юг / Центр — видно в инфо.")
    return "\n".join(lines)


async def get_continent_buff(session: AsyncSession) -> dict | None:
    raw = await get_meta(session, "continent_buff")
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    ends = data.get("ends_at")
    if not ends:
        return None
    from datetime import datetime

    ends_dt = datetime.fromisoformat(ends)
    if ends_dt.tzinfo is None:
        ends_dt = ends_dt.replace(tzinfo=timezone.utc)
    if utcnow() >= ends_dt:
        return None
    return data


async def maybe_resolve_week(session: AsyncSession) -> str | None:
    """В понедельник после полуночи МСК — наградить прошлую неделю."""
    now = utcnow().astimezone(MSK)
    if now.weekday() != 0 or now.hour > 1:
        return None
    last = await get_meta(session, "continent_resolved_week")
    # прошлый week id: чуть грубо — текущий уже новый в пн
    prev_key = await get_meta(session, "continent_prev_week")
    cur = week_id()
    if last == cur:
        return None
    # читаем scores прошлой метки
    score_key = prev_key or cur
    raw = await get_meta(session, f"continent_scores:{score_key}")
    if not raw and prev_key:
        return None
    scores = await _scores(session) if not prev_key else json.loads(raw or "{}")
    for b in BLOCS:
        scores.setdefault(b, 0)
    winner = max(BLOCS, key=lambda b: int(scores.get(b, 0)))
    if int(scores.get(winner, 0)) <= 0:
        await set_meta(session, "continent_resolved_week", cur)
        await set_meta(session, "continent_prev_week", cur)
        return None
    ends = utcnow() + timedelta(days=config.CONTINENT_WIN_DAYS)
    await set_meta(
        session,
        "continent_buff",
        json.dumps(
            {
                "bloc": winner,
                "work_mult": config.CONTINENT_WIN_WORK_MULT,
                "ends_at": ends.isoformat(),
            },
            ensure_ascii=False,
        ),
    )
    await set_meta(session, "continent_resolved_week", cur)
    await set_meta(session, "continent_prev_week", cur)
    # титул лидерам стран блока
    result = await session.execute(
        select(Nation).where(Nation.continent == winner)
    )
    for n in result.scalars().all():
        from db.models import Player

        lead = await session.execute(
            select(Player).where(Player.vk_id == n.leader_id)
        )
        leader = lead.scalar_one_or_none()
        if leader:
            await grant_title(session, leader, "continent_champ")
    msg = (
        f"🗺 Победа блока {continent_label(winner)}! "
        f"Всем странам блока +{int(config.CONTINENT_WIN_WORK_MULT * 100)}% "
        f"работы на {config.CONTINENT_WIN_DAYS} дн."
    )
    await add_event(session, "raid", msg, "")
    return msg


async def ensure_nation_continent(session: AsyncSession, nation: Nation) -> str:
    if nation.continent in BLOCS:
        return nation.continent
    nation.continent = assign_continent(nation.id)
    await session.commit()
    return nation.continent
