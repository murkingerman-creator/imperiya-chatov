"""Уровни игрока: XP и разблокировки."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from bot import config
from db.models import Player
from services.player import ensure_aware, utcnow


def xp_to_next(level: int) -> int:
    level = max(1, min(int(level), config.LEVEL_MAX))
    if level >= config.LEVEL_MAX:
        return 0
    return int(config.LEVEL_XP_BASE + level * config.LEVEL_XP_GROWTH)


def sync_level(player: Player) -> int:
    """Пересчитать level из накопленного xp."""
    remaining = max(0, int(player.xp or 0))
    lvl = 1
    while lvl < config.LEVEL_MAX:
        need = xp_to_next(lvl)
        if remaining < need:
            break
        remaining -= need
        lvl += 1
    player.level = lvl
    return lvl


def level_progress(player: Player) -> tuple[int, int, int]:
    """(level, xp_into_level, need_for_next)."""
    sync_level(player)
    lvl = int(player.level or 1)
    total = max(0, int(player.xp or 0))
    spent = 0
    for L in range(1, lvl):
        spent += xp_to_next(L)
    into = max(0, total - spent)
    need = xp_to_next(lvl)
    return lvl, into, need


def job_unlocked(player: Player, job: str) -> bool:
    req = config.JOB_LEVEL_REQ.get(job)
    if req is None:
        return True
    return int(player.level or 1) >= int(req)


def feature_unlocked(player: Player, feature: str) -> bool:
    req = config.FEATURE_LEVEL_REQ.get(feature, 1)
    return int(player.level or 1) >= int(req)


def unlocks_at_level(level: int) -> list[str]:
    lines = []
    for job, req in config.JOB_LEVEL_REQ.items():
        if req == level:
            title = config.JOBS.get(job, {}).get("title", job)
            lines.append(f"работа {title}")
    if config.SMUGGLE_LEVEL_REQ == level:
        lines.append("🕶 Контрабанда")
    labels = {
        "duel": "дуэли",
        "market_trade": "торг",
        "auction": "аукцион",
        "black_market": "чёрный рынок",
        "contracts": "контракты",
        "muster_join": "сбор на рейд",
    }
    for feat, req in config.FEATURE_LEVEL_REQ.items():
        if req == level:
            lines.append(labels.get(feat, feat))
    return lines


async def add_xp(
    session: AsyncSession, player: Player, amount: int, *, reason: str = ""
) -> dict:
    if amount <= 0:
        return {"gained": 0, "level_ups": [], "level": int(player.level or 1)}

    # бафф стипендии страны
    mult = 1.0
    if player.nation_id and player.nation:
        until = ensure_aware(player.nation.xp_buff_until)
        if until and until > utcnow():
            mult = float(config.TREASURY_SCHOLAR_XP_MULT)

    gained = int(round(amount * mult))
    old_lvl = int(player.level or 1)
    player.xp = int(player.xp or 0) + gained
    sync_level(player)
    new_lvl = int(player.level or 1)
    level_ups: list[str] = []
    for L in range(old_lvl + 1, new_lvl + 1):
        unlocked = unlocks_at_level(L)
        extra = f" · открыто: {', '.join(unlocked)}" if unlocked else ""
        level_ups.append(f"⬆ Уровень {L}!{extra}")
    await session.commit()
    return {
        "gained": gained,
        "level_ups": level_ups,
        "level": new_lvl,
        "reason": reason,
        "mult": mult,
    }


def format_level_line(player: Player) -> str:
    lvl, into, need = level_progress(player)
    if need <= 0:
        return f"⭐ Ур. {lvl} (макс)"
    filled = min(10, int(round(10 * into / need))) if need else 10
    bar = "█" * filled + "░" * (10 - filled)
    return f"⭐ Ур. {lvl} [{bar}] {into}/{need} XP"


def jobs_unlock_help(player: Player) -> str:
    lvl = int(player.level or 1)
    lines = [f"⭐ Твой уровень: {lvl}", "Работы:"]
    for job, req in sorted(config.JOB_LEVEL_REQ.items(), key=lambda x: x[1]):
        title = config.JOBS[job]["title"]
        mark = "✅" if lvl >= req else f"🔒{req}"
        lines.append(f"• {mark} {title}")
    sm = config.SMUGGLE_LEVEL_REQ
    mark = "✅" if lvl >= sm else f"🔒{sm}"
    lines.append(f"• {mark} 🕶 Контрабанда")
    return "\n".join(lines)
