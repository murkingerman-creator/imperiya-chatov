import random

from sqlalchemy.ext.asyncio import AsyncSession

from bot import config
from db.models import Player
from services.achievements import grant_title


async def on_job_done(session: AsyncSession, player: Player) -> dict:
    player.quest_jobs = (player.quest_jobs or 0) + 1
    await session.commit()
    return {
        "progress": player.quest_jobs,
        "needed": config.QUEST_JOBS_NEEDED,
        "ready": player.quest_jobs >= config.QUEST_JOBS_NEEDED
        and (player.quest_claimed or 0) < player.quest_jobs // config.QUEST_JOBS_NEEDED,
    }


async def claim_quest(session: AsyncSession, player: Player) -> dict:
    completed = (player.quest_jobs or 0) // config.QUEST_JOBS_NEEDED
    claimed = player.quest_claimed or 0
    if completed <= claimed:
        raise ValueError(
            f"Квест не готов. Работ: {player.quest_jobs}/{config.QUEST_JOBS_NEEDED}"
        )
    reward = random.randint(config.QUEST_REWARD_MIN, config.QUEST_REWARD_MAX)
    player.crowns += reward
    player.quest_claimed = claimed + 1
    title = await grant_title(session, player, "questor")
    await session.commit()
    return {"reward": reward, "crowns": player.crowns, "title": title}
