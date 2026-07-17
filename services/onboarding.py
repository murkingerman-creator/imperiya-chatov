"""Короткий онбординг: ежедневка → работа → страна/инвайт."""

from sqlalchemy.ext.asyncio import AsyncSession

from bot import config
from db.models import Player
from services.achievements import grant_title


# 0 = завершён; 1 = нужна ежедневка; 2 = нужна работа; 3 = страна или инвайт
STEP_DONE = 0
STEP_DAILY = 1
STEP_WORK = 2
STEP_NATION = 3


def ensure_onboarding_defaults(player: Player) -> None:
    """Новые игроки начинают с шага 1; у старых поле 0."""
    if player.onboarding_step is None:
        player.onboarding_step = STEP_DONE


def onboarding_prompt(player: Player) -> str | None:
    step = player.onboarding_step or STEP_DONE
    if step == STEP_DONE:
        return None
    if step == STEP_DAILY:
        return (
            "🌱 Квест новичка (1/3)\n"
            f"Нажми «🎁 Ежедневка» — получишь стрик и +{config.ONBOARD_REWARD_DAILY} крон за шаг."
        )
    if step == STEP_WORK:
        return (
            "🌱 Квест новичка (2/3)\n"
            f"Сделай любую «💼 Работу» — +{config.ONBOARD_REWARD_WORK} крон за шаг."
        )
    if step == STEP_NATION:
        return (
            "🌱 Квест новичка (3/3)\n"
            "Вступи в страну («🏛 Страна») или активируй инвайт друга.\n"
            f"Награда шага: +{config.ONBOARD_REWARD_NATION} крон + титул."
        )
    return None


async def advance_onboarding(
    session: AsyncSession,
    player: Player,
    event: str,
) -> str | None:
    """
    event: daily | work | nation
    Returns reward line or None.
    """
    step = player.onboarding_step or STEP_DONE
    if step == STEP_DONE:
        return None

    reward = 0
    title_line = ""
    if event == "daily" and step == STEP_DAILY:
        reward = config.ONBOARD_REWARD_DAILY
        player.crowns += reward
        player.onboarding_step = STEP_WORK
        msg = f"🌱 Шаг 1/3! +{reward} крон. Дальше — любая работа."
    elif event == "work" and step == STEP_WORK:
        reward = config.ONBOARD_REWARD_WORK
        player.crowns += reward
        player.onboarding_step = STEP_NATION
        msg = f"🌱 Шаг 2/3! +{reward} крон. Дальше — страна или инвайт."
    elif event == "nation" and step == STEP_NATION:
        reward = config.ONBOARD_REWARD_NATION
        player.crowns += reward
        player.onboarding_step = STEP_DONE
        t = await grant_title(session, player, "novice")
        if t:
            title_line = f"\n🏅 {t}"
        msg = f"🌱 Квест новичка завершён! +{reward} крон.{title_line}"
    else:
        return None

    await session.commit()
    return msg
