"""Багрепорты от игроков."""

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot import config
from db.models import BugReport, Player
from services.player import ensure_aware, utcnow


class BugError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


async def create_bug_report(
    session: AsyncSession, player: Player, text: str
) -> BugReport:
    body = (text or "").strip()
    if len(body) < config.BUG_MIN_LEN:
        raise BugError(f"Слишком коротко (минимум {config.BUG_MIN_LEN} символов).")
    if len(body) > config.BUG_MAX_LEN:
        raise BugError(f"Слишком длинно (максимум {config.BUG_MAX_LEN} символов).")

    result = await session.execute(
        select(BugReport)
        .where(
            BugReport.author_vk_id == player.vk_id,
            BugReport.status == "pending",
        )
        .order_by(BugReport.created_at.desc())
        .limit(1)
    )
    last_pending = result.scalar_one_or_none()
    if last_pending:
        raise BugError(
            f"У тебя уже есть открытый баг #{last_pending.id}. "
            f"Дождись решения админа."
        )

    result = await session.execute(
        select(BugReport)
        .where(BugReport.author_vk_id == player.vk_id)
        .order_by(BugReport.created_at.desc())
        .limit(1)
    )
    last = result.scalar_one_or_none()
    if last:
        created = ensure_aware(last.created_at)
        if created:
            ready = created + timedelta(hours=config.BUG_COOLDOWN_HOURS)
            if utcnow() < ready:
                left = int((ready - utcnow()).total_seconds() / 60) + 1
                raise BugError(f"Подожди ещё ~{left} мин перед новым репортом.")

    bug = BugReport(
        author_vk_id=player.vk_id,
        author_name=player.name or f"Игрок {player.vk_id}",
        text=body,
        status="pending",
    )
    session.add(bug)
    await session.commit()
    await session.refresh(bug)
    return bug


async def list_pending_bugs(
    session: AsyncSession, limit: int | None = None
) -> list[BugReport]:
    lim = limit or config.BUG_LIST_LIMIT
    result = await session.execute(
        select(BugReport)
        .where(BugReport.status == "pending")
        .order_by(BugReport.id.asc())
        .limit(lim)
    )
    return list(result.scalars().all())


async def get_bug(session: AsyncSession, bug_id: int) -> BugReport:
    bug = await session.get(BugReport, bug_id)
    if not bug:
        raise BugError(f"Баг #{bug_id} не найден.")
    return bug


def format_bugs_list(items: list[BugReport]) -> str:
    if not items:
        return "📭 Открытых багрепортов нет."
    lines = [f"🐛 Багрепорты ({len(items)}):", ""]
    for bug in items:
        preview = bug.text.replace("\n", " ")
        if len(preview) > 80:
            preview = preview[:77] + "…"
        lines.append(f"#{bug.id} {bug.author_name}: {preview}")
        lines.append(f"   {bug.text[:200]}{'…' if len(bug.text) > 200 else ''}")
        lines.append("")
    lines.append("Подтвердить (награда): !багпринять ID")
    lines.append("Отклонить: !баготклонить ID [причина]")
    return "\n".join(lines).strip()


async def accept_bug(session: AsyncSession, bug_id: int, note: str = "") -> dict:
    bug = await get_bug(session, bug_id)
    if bug.status != "pending":
        raise BugError(f"#{bug_id} уже закрыто ({bug.status}).")

    result = await session.execute(
        select(Player).where(Player.vk_id == bug.author_vk_id)
    )
    player = result.scalar_one_or_none()
    reward = config.BUG_REWARD
    if player:
        player.crowns += reward
    bug.status = "accepted"
    bug.reward = reward
    bug.admin_note = (note or "").strip()[:256]
    bug.resolved_at = utcnow()
    await session.commit()
    return {
        "bug": bug,
        "reward": reward,
        "crowns": player.crowns if player else None,
        "player": player,
    }


async def reject_bug(session: AsyncSession, bug_id: int, note: str = "") -> dict:
    bug = await get_bug(session, bug_id)
    if bug.status != "pending":
        raise BugError(f"#{bug_id} уже закрыто ({bug.status}).")
    bug.status = "rejected"
    bug.reward = 0
    bug.admin_note = (note or "").strip()[:256]
    bug.resolved_at = utcnow()
    await session.commit()
    return {"bug": bug}
