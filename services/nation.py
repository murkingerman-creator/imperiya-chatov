from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from bot import config
from db.models import Nation, Player
from services.player import regenerate_energy


class NationError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


CHAT_PEER_OFFSET = 2_000_000_000


def is_chat_peer(peer_id: int) -> bool:
    return peer_id >= CHAT_PEER_OFFSET


async def get_nation_by_chat(session: AsyncSession, peer_id: int) -> Nation | None:
    result = await session.execute(
        select(Nation)
        .options(selectinload(Nation.players))
        .where(Nation.chat_peer_id == peer_id)
    )
    return result.scalar_one_or_none()


async def get_nation_by_id(session: AsyncSession, nation_id: int) -> Nation | None:
    result = await session.execute(
        select(Nation)
        .options(selectinload(Nation.players))
        .where(Nation.id == nation_id)
    )
    return result.scalar_one_or_none()


async def get_nation_by_name(session: AsyncSession, name: str) -> Nation | None:
    result = await session.execute(
        select(Nation)
        .options(selectinload(Nation.players))
        .where(func.lower(Nation.name) == name.lower().strip())
    )
    return result.scalar_one_or_none()


async def count_citizens(session: AsyncSession, nation_id: int) -> int:
    result = await session.execute(
        select(func.count()).select_from(Player).where(Player.nation_id == nation_id)
    )
    return int(result.scalar_one())


async def found_nation(
    session: AsyncSession,
    player: Player,
    peer_id: int,
    name: str,
    flag_emoji: str = "🏛",
) -> Nation:
    regenerate_energy(player)

    if not is_chat_peer(peer_id):
        raise NationError("Основать страну можно только в беседе. Добавь бота в чат.")

    name = name.strip()
    if len(name) < 2 or len(name) > 32:
        raise NationError("Название страны: от 2 до 32 символов.")

    if player.nation_id:
        raise NationError("Ты уже гражданин другой страны. Сначала нельзя сменить в MVP.")

    existing = await get_nation_by_chat(session, peer_id)
    if existing:
        raise NationError(
            f"В этой беседе уже есть страна «{existing.flag_emoji} {existing.name}»."
        )

    if await get_nation_by_name(session, name):
        raise NationError("Страна с таким названием уже существует.")

    if player.crowns < config.NATION_FOUND_COST:
        raise NationError(
            f"Нужно {config.NATION_FOUND_COST} крон для основания (у тебя {player.crowns})."
        )

    player.crowns -= config.NATION_FOUND_COST
    nation = Nation(
        chat_peer_id=peer_id,
        name=name,
        flag_emoji=flag_emoji or "🏛",
        leader_id=player.vk_id,
        treasury=0,
    )
    session.add(nation)
    await session.flush()
    player.nation_id = nation.id
    await session.commit()
    await session.refresh(player, attribute_names=["nation"])
    await session.refresh(nation)
    return nation


async def join_nation(session: AsyncSession, player: Player, peer_id: int) -> Nation:
    if not is_chat_peer(peer_id):
        raise NationError("Вступить можно только из беседы своей будущей страны.")

    if player.nation_id:
        raise NationError("Ты уже состоишь в стране.")

    nation = await get_nation_by_chat(session, peer_id)
    if not nation:
        raise NationError("В этой беседе ещё нет страны. Оснуй её кнопкой «Основать».")

    player.nation_id = nation.id
    await session.commit()
    await session.refresh(player, attribute_names=["nation"])
    return nation


async def top_nations(session: AsyncSession, limit: int = 10) -> list[tuple[Nation, int]]:
    citizens = (
        select(Player.nation_id, func.count().label("cnt"))
        .where(Player.nation_id.is_not(None))
        .group_by(Player.nation_id)
        .subquery()
    )
    result = await session.execute(
        select(Nation, func.coalesce(citizens.c.cnt, 0))
        .outerjoin(citizens, Nation.id == citizens.c.nation_id)
        .order_by(Nation.treasury.desc(), Nation.id.asc())
        .limit(limit)
    )
    return list(result.all())


async def top_players(session: AsyncSession, limit: int = 10) -> list[Player]:
    result = await session.execute(
        select(Player).order_by(Player.crowns.desc(), Player.id.asc()).limit(limit)
    )
    return list(result.scalars().all())
