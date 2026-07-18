from datetime import timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import MetaKV, Nation, Player, SeasonScore
from services.achievements import grant_title
from services.empire import start_empire_decree
from services.player import utcnow

MSK = timezone(timedelta(hours=3))


def current_season_id() -> str:
    return utcnow().astimezone(MSK).strftime("%Y-%m")


async def add_points(session: AsyncSession, nation_id: int, points: int) -> SeasonScore:
    season_id = current_season_id()
    result = await session.execute(
        select(SeasonScore).where(
            SeasonScore.season_id == season_id, SeasonScore.nation_id == nation_id
        )
    )
    score = result.scalar_one_or_none()
    if not score:
        score = SeasonScore(season_id=season_id, nation_id=nation_id, points=0)
        session.add(score)
    score.points += points
    await session.commit()
    return score


async def top_seasons(session: AsyncSession, limit: int = 10) -> list[tuple[SeasonScore, Nation]]:
    result = await session.execute(
        select(SeasonScore, Nation)
        .join(Nation, Nation.id == SeasonScore.nation_id)
        .where(SeasonScore.season_id == current_season_id())
        .order_by(SeasonScore.points.desc(), Nation.id.asc())
        .limit(limit)
    )
    return list(result.all())


async def maybe_rotate_season(session: AsyncSession) -> list[str]:
    current = current_season_id()
    meta = await session.get(MetaKV, "last_season")
    if not meta:
        session.add(MetaKV(key="last_season", value=current))
        await session.commit()
        return []
    if meta.value == current:
        return []

    previous = meta.value
    result = await session.execute(
        select(SeasonScore, Nation, Player)
        .join(Nation, Nation.id == SeasonScore.nation_id)
        .join(Player, Player.vk_id == Nation.leader_id)
        .where(SeasonScore.season_id == previous)
        .order_by(SeasonScore.points.desc(), Nation.id.asc())
        .limit(3)
    )
    awards: list[str] = []
    rows = list(result.all())
    for rank, (score, nation, leader) in enumerate(rows, 1):
        title = await grant_title(session, leader, "empire_season")
        if title:
            awards.append(
                f"🏆 {rank}. {nation.flag_emoji} {nation.name} — {title}"
            )
        if rank == 1:
            until = await start_empire_decree(session, nation)
            awards.append(
                f"🏛 Указ Империи на 14 дней: +работы и удача лута для всех "
                f"(до {until.astimezone(MSK).strftime('%d.%m %H:%M')} МСК)"
            )
    meta.value = current
    await session.commit()
    return awards
