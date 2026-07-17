from sqlalchemy.ext.asyncio import AsyncSession

from bot import config
from db.models import Player


def parse_titles(player: Player) -> list[str]:
    raw = (player.titles or "").strip()
    if not raw:
        return []
    return [t for t in raw.split(",") if t]


def format_titles(player: Player) -> str:
    codes = parse_titles(player)
    if not codes:
        return "нет"
    return ", ".join(config.TITLE_LABELS.get(c, c) for c in codes)


async def grant_title(session: AsyncSession, player: Player, code: str) -> str | None:
    if code not in config.TITLE_LABELS:
        return None
    titles = parse_titles(player)
    if code in titles:
        return None
    titles.append(code)
    player.titles = ",".join(titles)
    await session.commit()
    return config.TITLE_LABELS[code]


async def check_after_raid(session: AsyncSession, player: Player) -> list[str]:
    gained = []
    player.raid_wins = (player.raid_wins or 0) + 1
    t = await grant_title(session, player, "first_raid")
    if t:
        gained.append(t)
    return gained


async def check_streak(session: AsyncSession, player: Player) -> list[str]:
    gained = []
    if (player.daily_streak or 0) >= 7:
        t = await grant_title(session, player, "streak_7")
        if t:
            gained.append(t)
    return gained


async def check_treasury(session: AsyncSession, player: Player) -> list[str]:
    gained = []
    if player.nation and (player.nation.treasury or 0) >= 10000:
        t = await grant_title(session, player, "treasury_10k")
        if t:
            gained.append(t)
    return gained
