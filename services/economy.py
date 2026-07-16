import random
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from bot import config
from db.models import Player
from services.player import ensure_aware, regenerate_energy, utcnow


class WorkError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


async def do_work(session: AsyncSession, player: Player) -> dict:
    regenerate_energy(player)
    now = utcnow()

    last = ensure_aware(player.last_work_at)
    if last:
        ready_at = last + timedelta(minutes=config.WORK_COOLDOWN_MINUTES)
        if now < ready_at:
            minutes_left = int((ready_at - now).total_seconds() / 60) + 1
            raise WorkError(f"Работать можно раз в час. Подожди ещё ~{minutes_left} мин.")

    if player.energy < 1:
        raise WorkError("Недостаточно энергии. Подожди восстановления.")

    gross = random.randint(config.WORK_REWARD_MIN, config.WORK_REWARD_MAX)
    tax = 0
    nation_name = None
    if player.nation_id and player.nation:
        nation_name = player.nation.name
        tax = max(1, int(gross * config.TAX_RATE))
        player.nation.treasury += tax

    net = gross - tax
    player.crowns += net
    player.energy -= 1
    player.last_work_at = now
    player.energy_updated_at = now

    await session.commit()

    return {
        "gross": gross,
        "tax": tax,
        "net": net,
        "crowns": player.crowns,
        "energy": player.energy,
        "nation_name": nation_name,
    }
