from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from bot import config
from db.models import Player
from services.player import ensure_aware, regenerate_energy, utcnow

MSK = timezone(timedelta(hours=3))


class DailyError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def _msk_date(dt: datetime) -> datetime.date:
    return dt.astimezone(MSK).date()


async def claim_daily(session: AsyncSession, player: Player) -> dict:
    regenerate_energy(player)
    now = utcnow()
    today = _msk_date(now)

    last = ensure_aware(player.last_daily_at)
    if last and _msk_date(last) == today:
        raise DailyError("Ежедневка уже получена сегодня. Завтра снова!")

    streak = player.daily_streak or 0
    if last:
        yesterday = today - timedelta(days=1)
        if _msk_date(last) == yesterday:
            streak = min(config.DAILY_STREAK_CAP, streak + 1)
        else:
            streak = 1
    else:
        streak = 1

    bonus = config.DAILY_STREAK_BONUS * min(streak, config.DAILY_STREAK_CAP)
    reward = config.DAILY_BASE + bonus
    player.daily_streak = streak
    player.last_daily_at = now
    player.crowns += reward
    await session.commit()

    return {
        "reward": reward,
        "streak": streak,
        "crowns": player.crowns,
        "base": config.DAILY_BASE,
        "bonus": bonus,
    }
