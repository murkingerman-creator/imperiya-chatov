import random
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from bot import config
from db.models import Player
from services.achievements import grant_title
from services.player import ensure_aware, regenerate_energy, utcnow
from services.world_events import get_active_event, tax_modifier, work_multiplier


class SmuggleError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def assert_not_jailed(player: Player) -> None:
    until = ensure_aware(player.jail_until)
    if until and utcnow() < until:
        left = int((until - utcnow()).total_seconds() / 60) + 1
        raise SmuggleError(f"Ты в тюрьме ещё ~{left} мин. Контрабанда недоступна.")


async def do_smuggle(session: AsyncSession, player: Player) -> dict:
    regenerate_energy(player)
    assert_not_jailed(player)
    now = utcnow()
    last = ensure_aware(player.last_smuggle_at)
    if last:
        ready = last + timedelta(minutes=config.SMUGGLE_COOLDOWN_MIN)
        if now < ready:
            mins = int((ready - now).total_seconds() / 60) + 1
            raise SmuggleError(f"Контрабанда на КД ~{mins} мин.")

    if player.energy < 1:
        raise SmuggleError("Недостаточно энергии.")

    ev = await get_active_event(session)
    success = random.random() < config.SMUGGLE_SUCCESS_CHANCE
    player.energy -= 1
    player.last_smuggle_at = now
    player.energy_updated_at = now

    if success:
        base = random.randint(config.SMUGGLE_REWARD_MIN, config.SMUGGLE_REWARD_MAX)
        gross = int(base * work_multiplier(ev) * 3)
        tax = 0
        if player.nation:
            rate = (player.nation.tax_rate or 0.1) + tax_modifier(ev)
            rate = max(0.0, min(0.4, rate))
            tax = max(1, int(gross * rate))
            player.nation.treasury += tax
        net = gross - tax
        player.crowns += net
        title = await grant_title(session, player, "smuggler")
        await session.commit()
        return {
            "success": True,
            "gross": gross,
            "tax": tax,
            "net": net,
            "crowns": player.crowns,
            "title": title,
            "jailed": False,
        }

    player.jail_until = now + timedelta(hours=config.SMUGGLE_JAIL_HOURS)
    fine = min(player.crowns, random.randint(30, 80))
    player.crowns -= fine
    await session.commit()
    return {
        "success": False,
        "fine": fine,
        "crowns": player.crowns,
        "jailed": True,
        "jail_hours": config.SMUGGLE_JAIL_HOURS,
    }
