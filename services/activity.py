from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Player
from services.player import utcnow


async def touch_chat_activity(session: AsyncSession, vk_id: int) -> bool:
    """Record a player's latest chat activity when they send a bot-visible message."""
    result = await session.execute(select(Player).where(Player.vk_id == vk_id))
    player = result.scalar_one_or_none()
    if not player:
        return False
    player.last_chat_seen_at = utcnow()
    await session.commit()
    return True
