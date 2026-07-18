"""Осада: 3 попытки / прогресс стены за 12ч."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from bot import config
from db.models import Nation, Player
from services.nation import get_nation_by_id, get_nation_by_name
from services.player import ensure_aware, utcnow
from services.roles import can_raid


class SiegeError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def _clear(nation: Nation) -> None:
    nation.siege_target_id = None
    nation.siege_progress = 0
    nation.siege_attempts = 0
    nation.siege_until = None


async def start_siege(session: AsyncSession, player: Player, target_name: str) -> dict:
    if not player.nation_id or not player.nation:
        raise SiegeError("Нужна страна.")
    if not await can_raid(session, player):
        raise SiegeError("Осаду объявляет лидер или воевода.")
    attacker = player.nation
    until = ensure_aware(attacker.siege_until)
    if until and until > utcnow() and attacker.siege_target_id:
        target = await get_nation_by_id(session, attacker.siege_target_id)
        tname = f"{target.flag_emoji} {target.name}" if target else "цели"
        raise SiegeError(
            f"Осада уже идёт → {tname}.\n"
            f"Бить нужно через ⚔ Война / Рейд по этой стране "
            f"(не кнопку «Осада» повторно).\n"
            f"Стена {attacker.siege_progress}/{config.SIEGE_NEED_PROGRESS}, "
            f"попытки {attacker.siege_attempts}/{config.SIEGE_MAX_ATTEMPTS}."
        )
    target = await get_nation_by_name(session, target_name)
    if not target:
        raise SiegeError(f"Страна «{target_name}» не найдена.")
    if target.id == attacker.id:
        raise SiegeError("Нельзя осаждать себя.")
    attacker.siege_target_id = target.id
    attacker.siege_progress = 0
    attacker.siege_attempts = 0
    attacker.siege_until = utcnow() + timedelta(hours=config.SIEGE_HOURS)
    await session.commit()
    return {"attacker": attacker, "defender": target, "until": attacker.siege_until}


async def siege_status(session: AsyncSession, nation: Nation) -> str | None:
    until = ensure_aware(nation.siege_until)
    if not until or until <= utcnow() or not nation.siege_target_id:
        if nation.siege_target_id:
            _clear(nation)
            await session.commit()
        return None
    target = await get_nation_by_id(session, nation.siege_target_id)
    name = f"{target.flag_emoji} {target.name}" if target else f"#{nation.siege_target_id}"
    left = max(1, int((until - utcnow()).total_seconds() / 60))
    return (
        f"🏰 Осада → {name}\n"
        f"Стена: {nation.siege_progress}/{config.SIEGE_NEED_PROGRESS} · "
        f"попытки {nation.siege_attempts}/{config.SIEGE_MAX_ATTEMPTS} · "
        f"ещё ~{left} мин\n"
        f"👉 Жми ⚔ Война и рейдь именно эту страну — каждый успешный рейд "
        f"ломает стену (+1). {config.SIEGE_NEED_PROGRESS} успеха за "
        f"{config.SIEGE_MAX_ATTEMPTS} попыток → финальный куш ×2."
    )


async def apply_siege_on_raid(
    session: AsyncSession,
    attacker: Nation,
    defender: Nation,
    *,
    success: bool,
) -> dict:
    """Обновить осаду после рейда. Возвращает флаги finale/failed/note."""
    out = {"finale": False, "failed": False, "note": "", "steal_mult": 1.0}
    until = ensure_aware(attacker.siege_until)
    if not until or until <= utcnow() or attacker.siege_target_id != defender.id:
        return out

    attacker.siege_attempts = int(attacker.siege_attempts or 0) + 1
    if success:
        attacker.siege_progress = int(attacker.siege_progress or 0) + 1
        out["note"] = (
            f"🏰 Стена: {attacker.siege_progress}/{config.SIEGE_NEED_PROGRESS}"
        )

    if attacker.siege_progress >= config.SIEGE_NEED_PROGRESS:
        out["finale"] = True
        out["steal_mult"] = float(config.SIEGE_FINALE_STEAL_MULT)
        out["note"] = "🏰 Стены пали! Финальный куш осады ×2"
        _clear(attacker)
        return out

    if attacker.siege_attempts >= config.SIEGE_MAX_ATTEMPTS:
        out["failed"] = True
        out["note"] = "🏰 Осада отбита — стены устояли"
        # утешение защитникам
        defender.treasury += 40
        _clear(attacker)
        return out

    return out
