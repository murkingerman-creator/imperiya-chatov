"""Предложения обновлений от игроков."""

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot import config
from db.models import Player, Suggestion
from services.player import ensure_aware, utcnow


class SuggestionError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


async def create_suggestion(
    session: AsyncSession, player: Player, text: str
) -> Suggestion:
    body = (text or "").strip()
    if len(body) < config.SUGGESTION_MIN_LEN:
        raise SuggestionError(
            f"Слишком коротко (минимум {config.SUGGESTION_MIN_LEN} символов)."
        )
    if len(body) > config.SUGGESTION_MAX_LEN:
        raise SuggestionError(
            f"Слишком длинно (максимум {config.SUGGESTION_MAX_LEN} символов)."
        )

    result = await session.execute(
        select(Suggestion)
        .where(
            Suggestion.author_vk_id == player.vk_id,
            Suggestion.status == "pending",
        )
        .order_by(Suggestion.created_at.desc())
        .limit(1)
    )
    last_pending = result.scalar_one_or_none()
    if last_pending:
        raise SuggestionError(
            f"У тебя уже есть открытое предложение #{last_pending.id}. "
            f"Дождись решения админа."
        )

    result = await session.execute(
        select(Suggestion)
        .where(Suggestion.author_vk_id == player.vk_id)
        .order_by(Suggestion.created_at.desc())
        .limit(1)
    )
    last = result.scalar_one_or_none()
    if last:
        created = ensure_aware(last.created_at)
        if created:
            ready = created + timedelta(hours=config.SUGGESTION_COOLDOWN_HOURS)
            if utcnow() < ready:
                left = int((ready - utcnow()).total_seconds() / 60) + 1
                raise SuggestionError(
                    f"Подожди ещё ~{left} мин перед новым предложением."
                )

    sug = Suggestion(
        author_vk_id=player.vk_id,
        author_name=player.name or f"Игрок {player.vk_id}",
        text=body,
        status="pending",
    )
    session.add(sug)
    await session.commit()
    await session.refresh(sug)
    return sug


async def list_pending(
    session: AsyncSession, limit: int | None = None
) -> list[Suggestion]:
    lim = limit or config.SUGGESTION_LIST_LIMIT
    result = await session.execute(
        select(Suggestion)
        .where(Suggestion.status == "pending")
        .order_by(Suggestion.id.asc())
        .limit(lim)
    )
    return list(result.scalars().all())


async def get_suggestion(session: AsyncSession, sug_id: int) -> Suggestion:
    sug = await session.get(Suggestion, sug_id)
    if not sug:
        raise SuggestionError(f"Предложение #{sug_id} не найдено.")
    return sug


def format_suggestion_short(sug: Suggestion) -> str:
    preview = sug.text.replace("\n", " ")
    if len(preview) > 80:
        preview = preview[:77] + "…"
    return f"#{sug.id} {sug.author_name}: {preview}"


def format_suggestions_list(items: list[Suggestion]) -> str:
    if not items:
        return "📭 Открытых предложений нет."
    lines = [f"💡 Предложения ({len(items)}):", ""]
    for sug in items:
        lines.append(format_suggestion_short(sug))
        lines.append(f"   {sug.text[:200]}{'…' if len(sug.text) > 200 else ''}")
        lines.append("")
    lines.append("Принять: !принять ID")
    lines.append("Отклонить: !отклонить ID [причина]")
    return "\n".join(lines).strip()


async def accept_suggestion(
    session: AsyncSession, sug_id: int, note: str = ""
) -> dict:
    sug = await get_suggestion(session, sug_id)
    if sug.status != "pending":
        raise SuggestionError(f"#{sug_id} уже закрыто ({sug.status}).")

    result = await session.execute(
        select(Player).where(Player.vk_id == sug.author_vk_id)
    )
    player = result.scalar_one_or_none()
    reward = config.SUGGESTION_REWARD
    if player:
        player.crowns += reward
    sug.status = "accepted"
    sug.reward = reward
    sug.admin_note = (note or "").strip()[:256]
    sug.resolved_at = utcnow()
    await session.commit()
    return {
        "suggestion": sug,
        "reward": reward,
        "crowns": player.crowns if player else None,
        "player": player,
    }


async def reject_suggestion(
    session: AsyncSession, sug_id: int, note: str = ""
) -> dict:
    sug = await get_suggestion(session, sug_id)
    if sug.status != "pending":
        raise SuggestionError(f"#{sug_id} уже закрыто ({sug.status}).")
    sug.status = "rejected"
    sug.reward = 0
    sug.admin_note = (note or "").strip()[:256]
    sug.resolved_at = utcnow()
    await session.commit()
    return {"suggestion": sug}
