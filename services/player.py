from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from bot import config
from db.models import Player


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def ensure_aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


async def get_or_create_player(
    session: AsyncSession, vk_id: int, name: str = ""
) -> Player:
    result = await session.execute(
        select(Player).options(selectinload(Player.nation)).where(Player.vk_id == vk_id)
    )
    player = result.scalar_one_or_none()
    if player:
        if name and player.name != name:
            player.name = name
        regenerate_energy(player)
        return player

    player = Player(
        vk_id=vk_id,
        name=name or f"Игрок {vk_id}",
        crowns=config.START_CROWNS,
        energy=config.MAX_ENERGY,
        energy_updated_at=utcnow(),
    )
    session.add(player)
    await session.commit()
    await session.refresh(player, attribute_names=["nation"])
    return player


def regenerate_energy(player: Player) -> None:
    now = utcnow()
    updated = ensure_aware(player.energy_updated_at) or now
    if player.energy >= config.MAX_ENERGY:
        player.energy_updated_at = now
        return

    minutes = (now - updated).total_seconds() / 60
    gained = int(minutes // config.ENERGY_REGEN_MINUTES)
    if gained <= 0:
        return

    player.energy = min(config.MAX_ENERGY, player.energy + gained)
    player.energy_updated_at = updated + timedelta(
        minutes=gained * config.ENERGY_REGEN_MINUTES
    )
    if player.energy >= config.MAX_ENERGY:
        player.energy_updated_at = now


def energy_next_in_minutes(player: Player) -> int | None:
    if player.energy >= config.MAX_ENERGY:
        return None
    updated = ensure_aware(player.energy_updated_at) or utcnow()
    elapsed = (utcnow() - updated).total_seconds() / 60
    left = config.ENERGY_REGEN_MINUTES - elapsed
    return max(1, int(left + 0.999))


async def get_player(session: AsyncSession, vk_id: int) -> Player | None:
    result = await session.execute(
        select(Player).options(selectinload(Player.nation)).where(Player.vk_id == vk_id)
    )
    return result.scalar_one_or_none()
