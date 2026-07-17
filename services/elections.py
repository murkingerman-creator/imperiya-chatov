from collections import Counter
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot import config
from db.models import ElectionVote, Nation, Player
from services.achievements import grant_title
from services.player import ensure_aware, utcnow


class ElectionError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def election_key(nation_id: int) -> str:
    # week bucket
    week = utcnow().strftime("%Y-W%W")
    return f"{nation_id}:{week}"


async def can_start_or_vote(session: AsyncSession, nation: Nation) -> str:
    return election_key(nation.id)


async def cast_vote(
    session: AsyncSession, voter: Player, candidate_vk_id: int
) -> dict:
    if not voter.nation_id or not voter.nation:
        raise ElectionError("Нужно быть гражданином.")
    nation = voter.nation
    key = election_key(nation.id)

    # one vote per voter per election
    existing = await session.execute(
        select(ElectionVote).where(
            ElectionVote.election_key == key,
            ElectionVote.voter_vk_id == voter.vk_id,
        )
    )
    if existing.scalar_one_or_none():
        raise ElectionError("Ты уже голосовал на этих выборах.")

    cand = await session.execute(
        select(Player).where(
            Player.vk_id == candidate_vk_id, Player.nation_id == nation.id
        )
    )
    if not cand.scalar_one_or_none():
        raise ElectionError("Кандидат не гражданин вашей страны.")

    session.add(
        ElectionVote(
            nation_id=nation.id,
            voter_vk_id=voter.vk_id,
            candidate_vk_id=candidate_vk_id,
            election_key=key,
        )
    )
    await session.commit()
    return {"key": key}


async def finish_election(session: AsyncSession, nation: Nation) -> dict:
    key = election_key(nation.id)
    last = ensure_aware(nation.election_at)
    if last and f"{nation.id}:{last.strftime('%Y-W%W')}" == key:
        raise ElectionError("Выборы этой недели уже завершены.")

    result = await session.execute(
        select(ElectionVote).where(ElectionVote.election_key == key)
    )
    votes = list(result.scalars().all())
    if len(votes) < 2:
        raise ElectionError("Мало голосов (нужно минимум 2).")

    counts = Counter(v.candidate_vk_id for v in votes)
    winner_id, win_votes = counts.most_common(1)[0]
    nation.leader_id = winner_id
    nation.election_at = utcnow()
    winner = await session.execute(select(Player).where(Player.vk_id == winner_id))
    w = winner.scalar_one()
    title = await grant_title(session, w, "emperor")
    await session.commit()
    return {
        "winner": w,
        "votes": win_votes,
        "total": len(votes),
        "title": title,
    }


async def election_status(session: AsyncSession, nation: Nation) -> str:
    key = election_key(nation.id)
    result = await session.execute(
        select(ElectionVote).where(ElectionVote.election_key == key)
    )
    votes = list(result.scalars().all())
    if not votes:
        return "Голосов пока нет. Голосуй: выборы @кандидат или кнопка."
    counts = Counter(v.candidate_vk_id for v in votes)
    lines = [f"🗳 Выборы ({len(votes)} голосов):"]
    for vid, c in counts.most_common(5):
        p = await session.execute(select(Player).where(Player.vk_id == vid))
        pl = p.scalar_one_or_none()
        name = pl.name if pl else str(vid)
        lines.append(f"• {name}: {c}")
    return "\n".join(lines)
