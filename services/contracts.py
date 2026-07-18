"""Биржа контрактов страны."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot import config
from db.models import NationContract, Player
from services.roles import can_treasury


class ContractError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


JOB_LABEL = {
    "mine": "шахта",
    "market": "рынок",
    "guard": "охрана",
    "fish": "рыбалка",
    "farm": "поле",
    "forge": "кузня",
    "tavern": "таверна",
}


async def create_contract(
    session: AsyncSession, player: Player, job: str, need: int, reward: int
) -> NationContract:
    if job not in JOB_LABEL:
        raise ContractError("Работа: mine/market/guard/fish/farm/forge/tavern")
    if not player.nation_id or not player.nation:
        raise ContractError("Нужна страна.")
    if not await can_treasury(session, player):
        raise ContractError("Контракт выставляет лидер или казначей.")
    need = max(config.CONTRACT_MIN_NEED, min(config.CONTRACT_MAX_NEED, int(need)))
    reward = max(config.CONTRACT_MIN_REWARD, min(config.CONTRACT_MAX_REWARD, int(reward)))
    if player.nation.treasury < reward:
        raise ContractError("В казне нет столько на награду.")
    player.nation.treasury -= reward  # резерв
    row = NationContract(
        nation_id=player.nation.id,
        job=job,
        need=need,
        progress=0,
        reward=reward,
        active=True,
        created_by=player.vk_id,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def list_contracts(session: AsyncSession, nation_id: int) -> list[NationContract]:
    result = await session.execute(
        select(NationContract).where(
            NationContract.nation_id == nation_id,
            NationContract.active.is_(True),
        )
    )
    return list(result.scalars().all())


async def on_job_for_contracts(
    session: AsyncSession, player: Player, job: str
) -> str | None:
    if not player.nation_id:
        return None
    contracts = await list_contracts(session, player.nation_id)
    for c in contracts:
        if c.job != job:
            continue
        c.progress += 1
        if c.progress >= c.need:
            c.active = False
            player.crowns += c.reward
            await session.commit()
            return (
                f"📜 Контракт выполнен ({JOB_LABEL.get(job, job)})! "
                f"+{c.reward}💰 из казны"
            )
        await session.commit()
        return (
            f"📜 Контракт: {c.progress}/{c.need} ({JOB_LABEL.get(job, job)})"
        )
    return None


def format_contracts(rows: list[NationContract]) -> str:
    if not rows:
        return "📜 Контрактов нет. Лидер: контракт mine 5 100"
    lines = ["📜 Контракты страны:"]
    for c in rows:
        lines.append(
            f"• #{c.id} {JOB_LABEL.get(c.job, c.job)} "
            f"{c.progress}/{c.need} → {c.reward}💰"
        )
    return "\n".join(lines)
