from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot import config
from db.models import ChatWar, Nation
from services.nation import get_nation_by_id, get_nation_by_name
from services.player import ensure_aware, utcnow


class ChatWarError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


async def start_war(
    session: AsyncSession, nation_a: Nation, target_name: str
) -> ChatWar:
    other = await get_nation_by_name(session, target_name)
    if not other:
        raise ChatWarError("Страна не найдена.")
    if other.id == nation_a.id:
        raise ChatWarError("Нельзя объявить войну себе.")

    # check active
    result = await session.execute(
        select(ChatWar).where(ChatWar.active.is_(True))
    )
    for w in result.scalars().all():
        if nation_a.id in (w.nation_a_id, w.nation_b_id) or other.id in (
            w.nation_a_id,
            w.nation_b_id,
        ):
            raise ChatWarError("Одна из стран уже в войне бесед.")

    stake = config.CHAT_WAR_STAKE
    if nation_a.treasury < stake or other.treasury < stake:
        raise ChatWarError(f"У обеих стран нужно ≥{stake} в казне.")

    nation_a.treasury -= stake
    other.treasury -= stake
    war = ChatWar(
        nation_a_id=nation_a.id,
        nation_b_id=other.id,
        stake=stake,
        active=True,
        ends_at=utcnow() + timedelta(hours=config.CHAT_WAR_HOURS),
    )
    session.add(war)
    await session.commit()
    await session.refresh(war)
    return war


async def add_score(session: AsyncSession, nation_id: int, points: int = 1) -> ChatWar | None:
    result = await session.execute(
        select(ChatWar).where(ChatWar.active.is_(True))
    )
    for w in result.scalars().all():
        ends = ensure_aware(w.ends_at)
        if ends and utcnow() >= ends:
            continue
        if w.nation_a_id == nation_id:
            w.score_a += points
            await session.commit()
            return w
        if w.nation_b_id == nation_id:
            w.score_b += points
            await session.commit()
            return w
    return None


async def finish_due_wars(session: AsyncSession) -> list[str]:
    result = await session.execute(select(ChatWar).where(ChatWar.active.is_(True)))
    messages = []
    for w in result.scalars().all():
        ends = ensure_aware(w.ends_at)
        if not ends or utcnow() < ends:
            continue
        w.active = False
        a = await get_nation_by_id(session, w.nation_a_id)
        b = await get_nation_by_id(session, w.nation_b_id)
        pot = w.stake * 2
        from bot import config
        from services.season import add_points

        if w.score_a > w.score_b and a:
            a.treasury += pot
            winner = f"{a.flag_emoji} {a.name}"
            await add_points(session, a.id, config.SEASON_CHATWAR_WIN)
        elif w.score_b > w.score_a and b:
            b.treasury += pot
            winner = f"{b.flag_emoji} {b.name}"
            await add_points(session, b.id, config.SEASON_CHATWAR_WIN)
        else:
            if a:
                a.treasury += w.stake
            if b:
                b.treasury += w.stake
            winner = "ничья (ставки возвращены)"
        an = a.name if a else "?"
        bn = b.name if b else "?"
        messages.append(
            f"⚔ Война бесед окончена: {an} {w.score_a}:{w.score_b} {bn}. Победа: {winner}"
        )
    await session.commit()
    return messages


async def active_war_text(session: AsyncSession) -> str:
    result = await session.execute(
        select(ChatWar).where(ChatWar.active.is_(True)).order_by(ChatWar.id.desc())
    )
    wars = list(result.scalars().all())
    if not wars:
        return "Сейчас нет войн бесед."
    lines = ["⚔ Активные войны бесед:"]
    for w in wars:
        a = await get_nation_by_id(session, w.nation_a_id)
        b = await get_nation_by_id(session, w.nation_b_id)
        an = f"{a.flag_emoji} {a.name}" if a else "?"
        bn = f"{b.flag_emoji} {b.name}" if b else "?"
        lines.append(f"• {an} {w.score_a}:{w.score_b} {bn} (банк {w.stake*2})")
    return "\n".join(lines)
