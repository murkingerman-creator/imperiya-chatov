"""Личная сага на 7 дней."""

from __future__ import annotations

from datetime import timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from bot import config
from db.models import Player
from services.achievements import grant_title
from services.chronicle_store import add_event
from services.player import ensure_aware, utcnow

MSK = timezone(timedelta(hours=3))

DAY_TASKS = [
    "Сделай ежедневку",
    "Выполни любую работу",
    "Загляни в профиль и страну",
    "Сделай 2 работы",
    "Посети торг или лавку",
    "Сделай работу + ежедневку",
    "Финал: работа дня героя",
]


def saga_status(player: Player) -> str:
    day = int(player.saga_day or 0)
    if day <= 0:
        return (
            "📖 Личная сага не начата.\n"
            "Напиши «сага старт» — 7 дней квестов, титул и хроника."
        )
    if day > config.SAGA_DAYS:
        return "📖 Сага завершена. Ты — герой летописи."
    task = DAY_TASKS[min(day - 1, len(DAY_TASKS) - 1)]
    claimed = int(player.saga_claimed_day or 0)
    ready = "можно сдать" if claimed < day else "сегодня уже сдано — завтра новый день"
    return (
        f"📖 Сага: день {day}/{config.SAGA_DAYS}\n"
        f"Задание: {task}\n"
        f"Статус: {ready}\n"
        f"Сдать: «сага сдать» (после действия дня)"
    )


async def start_saga(session: AsyncSession, player: Player) -> str:
    if int(player.saga_day or 0) > 0 and int(player.saga_day or 0) <= config.SAGA_DAYS:
        return saga_status(player)
    if int(player.saga_day or 0) > config.SAGA_DAYS:
        return "Сага уже пройдена."
    player.saga_day = 1
    player.saga_claimed_day = 0
    await session.commit()
    return "📖 Сага началась! День 1: сделай ежедневку, затем «сага сдать»."


async def tick_saga_day(session: AsyncSession, player: Player) -> None:
    """Сдвиг дня саги раз в сутки МСК при активности."""
    day = int(player.saga_day or 0)
    if day <= 0 or day > config.SAGA_DAYS:
        return
    # храним прогресс дней через claimed; новый календарный день = +saga_day если claimed
    # упрощение: при сдаче увеличиваем day


async def claim_saga(session: AsyncSession, player: Player) -> str:
    day = int(player.saga_day or 0)
    if day <= 0:
        return "Сначала «сага старт»."
    if day > config.SAGA_DAYS:
        return "Сага уже завершена."
    claimed = int(player.saga_claimed_day or 0)
    if claimed >= day:
        return "Сегодняшний день саги уже сдан. Завтра продолжим."

    # лёгкая проверка «было действие»: energy spent / daily / work recently
    from services.player import ensure_aware

    active = False
    for field in ("last_daily_at", "last_work_at", "last_mine_at", "last_market_at"):
        ts = ensure_aware(getattr(player, field, None))
        if ts and (utcnow() - ts).total_seconds() < 36 * 3600:
            active = True
            break
    if not active and (player.quest_jobs or 0) > 0:
        active = True
    if not active:
        return "Сначала сделай дело дня (работа/ежедневка), потом сдавай."

    player.saga_claimed_day = day
    player.crowns += int(config.SAGA_DAY_REWARD)
    from services.levels import add_xp

    await add_xp(session, player, config.XP_SAGA_DAY, reason="сага")
    msg = f"📖 День {day} саги сдан! +{config.SAGA_DAY_REWARD}💰"

    if day >= config.SAGA_DAYS:
        player.saga_day = config.SAGA_DAYS + 1
        player.crowns += int(config.SAGA_FINISH_REWARD)
        title = await grant_title(session, player, "saga_hero")
        await add_event(
            session,
            "invite",
            f"📖 Так родился герой: {player.name} завершил личную сагу!",
            "",
        )
        msg += (
            f"\n🏆 Сага завершена! +{config.SAGA_FINISH_REWARD}💰"
            + (f" · {title}" if title else "")
        )
    else:
        player.saga_day = day + 1
        msg += f"\nЗавтра — день {day + 1}: {DAY_TASKS[day]}"

    await session.commit()
    return msg
