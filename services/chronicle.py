from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import GROUP_ID
from db.models import ChronicleEvent
from services.chronicle_store import get_meta, set_meta
from services.nation import top_nations
from services.notify import post_wall
from services.player import utcnow

MSK = timezone(timedelta(hours=3))


async def build_digest(session: AsyncSession) -> str:
    rows = await top_nations(session, 5)
    lines = [
        "📜 Хроника Империи чатов",
        f"Дата: {utcnow().astimezone(MSK).strftime('%d.%m.%Y')}",
        "",
        "🏆 Топ стран:",
    ]
    if not rows:
        lines.append("— пока пусто —")
    else:
        for i, (nation, citizens) in enumerate(rows, 1):
            lines.append(
                f"{i}. {nation.flag_emoji} {nation.name} — "
                f"💰 {nation.treasury} · 👥 {citizens}"
            )

    result = await session.execute(
        select(ChronicleEvent)
        .order_by(ChronicleEvent.id.desc())
        .limit(12)
    )
    events = list(reversed(result.scalars().all()))
    lines.append("")
    lines.append("📰 События:")
    if not events:
        lines.append("— тишина на границах —")
    else:
        for ev in events[-8:]:
            lines.append(f"• {ev.text}")

    lines.append("")
    lines.append("Играй в сообщениях сообщества · Империя чатов")
    return "\n".join(lines)


async def maybe_post_daily_chronicle(api, session: AsyncSession) -> bool:
    """Пост около 20:00 MSK раз в сутки."""
    now = utcnow().astimezone(MSK)
    if now.hour < 20:
        return False
    today = now.strftime("%Y-%m-%d")
    last = await get_meta(session, "last_chronicle_post_date")
    if last == today:
        return False

    await force_post_chronicle(api, session)
    return True


async def force_post_chronicle(api, session: AsyncSession) -> str:
    """Принудительный пост хроники (админка)."""
    text = await build_digest(session)
    await post_wall(api, text)
    today = utcnow().astimezone(MSK).strftime("%Y-%m-%d")
    await set_meta(session, "last_chronicle_post_date", today)
    result = await session.execute(
        select(ChronicleEvent).order_by(ChronicleEvent.id.desc()).offset(50)
    )
    for old in result.scalars().all():
        await session.delete(old)
    await session.commit()
    return text
