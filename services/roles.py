from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import NationRole, Player


class RolesError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


ROLES = {"warlord", "treasurer", "herald"}


async def get_role(
    session: AsyncSession, nation_id: int, role: str
) -> NationRole | None:
    result = await session.execute(
        select(NationRole).where(
            NationRole.nation_id == nation_id, NationRole.role == role
        )
    )
    return result.scalar_one_or_none()


async def get_player_role(
    session: AsyncSession, nation_id: int, vk_id: int
) -> str | None:
    result = await session.execute(
        select(NationRole.role).where(
            NationRole.nation_id == nation_id, NationRole.vk_id == vk_id
        )
    )
    return result.scalar_one_or_none()


async def set_role(
    session: AsyncSession, leader: Player, target_vk_id: int, role: str
) -> str:
    if role not in ROLES:
        raise RolesError("Неизвестная государственная должность.")
    if not leader.nation_id or not leader.nation:
        raise RolesError("Ты не состоишь в стране.")
    if leader.nation.leader_id != leader.vk_id:
        raise RolesError("Назначать должности может только лидер.")

    result = await session.execute(
        select(Player).where(
            Player.vk_id == target_vk_id, Player.nation_id == leader.nation_id
        )
    )
    target = result.scalar_one_or_none()
    if not target:
        raise RolesError("Игрок не найден среди граждан страны.")
    if target.vk_id == leader.vk_id:
        raise RolesError("Лидер уже обладает всеми полномочиями.")

    await session.execute(
        delete(NationRole).where(
            NationRole.nation_id == leader.nation_id,
            (NationRole.role == role) | (NationRole.vk_id == target_vk_id),
        )
    )
    session.add(NationRole(nation_id=leader.nation_id, vk_id=target_vk_id, role=role))
    await session.commit()
    return f"{target.name} назначен: {role}."


async def clear_role(session: AsyncSession, leader: Player, role: str) -> str:
    if role not in ROLES:
        raise RolesError("Неизвестная государственная должность.")
    if not leader.nation_id or not leader.nation:
        raise RolesError("Ты не состоишь в стране.")
    if leader.nation.leader_id != leader.vk_id:
        raise RolesError("Снимать с должности может только лидер.")
    row = await get_role(session, leader.nation_id, role)
    if not row:
        raise RolesError("Эта должность сейчас свободна.")
    await session.delete(row)
    await session.commit()
    return f"Должность {role} освобождена."


async def _has_authority(
    session: AsyncSession, player: Player, role: str
) -> bool:
    if not player.nation_id or not player.nation:
        return False
    if player.nation.leader_id == player.vk_id:
        return True
    return await get_player_role(session, player.nation_id, player.vk_id) == role


async def can_raid(session: AsyncSession, player: Player) -> bool:
    return await _has_authority(session, player, "warlord")


async def can_treasury(session: AsyncSession, player: Player) -> bool:
    return await _has_authority(session, player, "treasurer")


async def can_herald(session: AsyncSession, player: Player) -> bool:
    return await _has_authority(session, player, "herald")
