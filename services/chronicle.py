"""Ежедневная хроника на стену сообщества."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot import config
from db.models import ChronicleEvent
from services.chronicle_store import get_meta, set_meta
from services.flash_events import get_flash_event
from services.nation import top_nations
from services.notify import post_wall
from services.player import utcnow
from services.world_events import format_event, get_active_event

MSK = timezone(timedelta(hours=3))

_MONTHS_RU = (
    "",
    "января",
    "февраля",
    "марта",
    "апреля",
    "мая",
    "июня",
    "июля",
    "августа",
    "сентября",
    "октября",
    "ноября",
    "декабря",
)

# event_type -> (section_title, intro_line)
_SECTIONS: list[tuple[str, str, str]] = [
    (
        "found",
        "🏛 Основаны державы",
        "На карте Империи вспыхнули новые знамёна — поздравляем правителей!",
    ),
    (
        "raid",
        "⚔ Клинки и казны",
        "Где гремели барабаны — там менялись границы богатств:",
    ),
    (
        "loot",
        "💎 Редкие находки",
        "Судьба улыбнулась искателям — из руды и тени вышли сокровища:",
    ),
    (
        "mythic",
        "🟥 Мифы Империи",
        "Пробудились легенды — мифические артефакты явили себя миру:",
    ),
    (
        "invite",
        "📨 Новые граждане",
        "В ряды держав встали новые имена:",
    ),
    (
        "dissolve",
        "🗑 Ушли в историю",
        "Не все знамёна устояли. В летописи осталось:",
    ),
]


def _date_ru(dt: datetime) -> str:
    local = dt.astimezone(MSK)
    return f"{local.day} {_MONTHS_RU[local.month]} {local.year}"


def _clean_bullet(text: str) -> str:
    t = (text or "").strip().replace("\n", " ")
    # убрать дублирующие префиксы, если уже есть в заголовке секции
    for prefix in ("Основана ", "Рейд ", "Страна "):
        if t.startswith(prefix):
            break
    return t


async def build_digest(session: AsyncSession) -> str:
    now = utcnow()
    cutoff = now - timedelta(hours=36)

    result = await session.execute(
        select(ChronicleEvent)
        .where(ChronicleEvent.created_at >= cutoff)
        .order_by(ChronicleEvent.id.asc())
        .limit(80)
    )
    events = list(result.scalars().all())

    # fallback: если по created_at пусто (старые строки без tz) — последние записи
    if not events:
        result = await session.execute(
            select(ChronicleEvent).order_by(ChronicleEvent.id.desc()).limit(40)
        )
        events = list(reversed(result.scalars().all()))

    by_type: dict[str, list[ChronicleEvent]] = defaultdict(list)
    for ev in events:
        by_type[ev.event_type or "info"].append(ev)

    lines: list[str] = [
        "📜 Хроника Империи чатов",
        "━━━━━━━━━━━━━━━━━━━━",
        f"🗓 {_date_ru(now)}",
        "",
        "В мире произошли события!",
        "Летописцы собрали главу суток — читай и пиши свою.",
        "",
    ]

    any_section = False
    for key, title, intro in _SECTIONS:
        items = by_type.get(key) or []
        if not items:
            continue
        any_section = True
        lines.append(title)
        lines.append(intro)
        # лимит строк на секцию, без дублей текста
        seen: set[str] = set()
        shown = 0
        for ev in items:
            bullet = _clean_bullet(ev.text)
            if not bullet or bullet in seen:
                continue
            seen.add(bullet)
            lines.append(f"• {bullet}")
            shown += 1
            if shown >= 12:
                extra = len(items) - shown
                if extra > 0:
                    lines.append(f"• …и ещё {extra}")
                break
        lines.append("")

    # прочие типы
    known = {k for k, _, _ in _SECTIONS}
    other = [ev for ev in events if (ev.event_type or "info") not in known]
    if other:
        any_section = True
        lines.append("📰 Прочие вести")
        lines.append("Ещё шептали на площадях:")
        for ev in other[-8:]:
            lines.append(f"• {_clean_bullet(ev.text)}")
        lines.append("")

    if not any_section:
        lines.append("🕊 На границах тишина.")
        lines.append("Ни рейдов, ни новых знамён — Империя набирает силы.")
        lines.append("")

    # знамения (ивент дня + вспышка)
    daily = await get_active_event(session)
    flash = await get_flash_event(session)
    if daily or flash:
        lines.append("🌤 Знамения суток")
        if daily:
            lines.append(f"• {format_event(daily)}")
        if flash:
            # короткая строка без многострочного оформления
            lines.append(f"• {flash['title']}: {flash['desc']}")
        lines.append("")

    # топ стран
    rows = await top_nations(session, 5)
    lines.append("🏆 Сильнейшие державы")
    if not rows:
        lines.append("• Пока пусто — основать страну может каждый чат.")
    else:
        lines.append("Кто держит казну и народ:")
        for i, (nation, citizens) in enumerate(rows, 1):
            medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"{i}.")
            lines.append(
                f"{medal} {nation.flag_emoji} {nation.name} — "
                f"💰 {nation.treasury} · 👥 {citizens}"
            )
    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append("⚔ Пиши боту сообщества «Империя чатов»")
    lines.append("и впиши своё имя в следующую главу.")
    return "\n".join(lines)


async def maybe_post_daily_chronicle(api, session: AsyncSession) -> bool:
    """Пост около 00:00 MSK раз в сутки."""
    now = utcnow().astimezone(MSK)
    # окно 00:00–00:59 (фон каждые 15 мин)
    if now.hour != 0:
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
        select(ChronicleEvent).order_by(ChronicleEvent.id.desc()).offset(80)
    )
    for old in result.scalars().all():
        await session.delete(old)
    await session.commit()
    return text


async def post_flash(api, session: AsyncSession, text: str) -> bool:
    """Post a short wall announcement, respecting the global flash cooldown."""
    now = utcnow()
    raw_last = await get_meta(session, "last_flash_at")
    if raw_last:
        try:
            last = datetime.fromisoformat(raw_last)
            if last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)
            if now < last + timedelta(minutes=config.WALL_FLASH_COOLDOWN_MIN):
                return False
        except ValueError:
            pass
    await post_wall(api, text)
    await set_meta(session, "last_flash_at", now.isoformat())
    return True
