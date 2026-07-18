"""Недовольство и переворот."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from bot import config
from db.models import Nation, Player
from services.player import ensure_aware, utcnow


class DiscontentError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


async def protest(session: AsyncSession, player: Player) -> dict:
    if not player.nation_id or not player.nation:
        raise DiscontentError("Нужна страна.")
    if player.nation.leader_id == player.vk_id:
        raise DiscontentError("Лидер не может протестовать против себя.")
    last = ensure_aware(player.last_protest_at)
    if last and last + timedelta(hours=config.DISCONTENT_PROTEST_CD_HOURS) > utcnow():
        raise DiscontentError("Протест уже был недавно. Подожди.")
    nation = player.nation
    nation.discontent = int(nation.discontent or 0) + int(config.DISCONTENT_PROTEST)
    player.last_protest_at = utcnow()
    coup = nation.discontent >= config.DISCONTENT_THRESHOLD
    if coup:
        nation.discontent = 0
        # сброс «недавних выборов» — можно голосовать снова
        nation.election_at = None
    await session.commit()
    return {"nation": nation, "value": nation.discontent, "coup": coup}


async def on_raid_fail(session: AsyncSession, nation: Nation) -> None:
    nation.discontent = int(nation.discontent or 0) + int(config.DISCONTENT_RAID_FAIL)
    if nation.discontent > config.DISCONTENT_THRESHOLD + 5:
        nation.discontent = config.DISCONTENT_THRESHOLD + 5
    await session.commit()


def discontent_line(nation: Nation) -> str:
    v = int(nation.discontent or 0)
    return f"😤 Недовольство: {v}/{config.DISCONTENT_THRESHOLD}"
