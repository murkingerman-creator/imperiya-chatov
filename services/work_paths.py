"""Ветки мастерства fish/forge."""

from __future__ import annotations

from bot import config
from db.models import Player
from services.professions import get_counts, job_rank

PATHS = {
    "fish:net": {"job": "fish", "label": "🎣 Сети", "desc": "+к доходу рыбалки"},
    "fish:spear": {"job": "fish", "label": "🔱 Гарпун", "desc": "+к доходу рыбалки"},
    "forge:arms": {"job": "forge", "label": "⚔ Оружие", "desc": "+к доходу кузни"},
    "forge:shoes": {"job": "forge", "label": "🐴 Подковы", "desc": "+к доходу кузни"},
}


def path_job(path: str) -> str | None:
    info = PATHS.get(path or "")
    return info["job"] if info else None


def format_path(player: Player) -> str:
    p = (getattr(player, "work_path", None) or "").strip()
    if not p or p not in PATHS:
        return "не выбран"
    return PATHS[p]["label"]


def can_choose_path(player: Player, job: str) -> bool:
    """С ранга ученик+ по этой работе."""
    return job_rank(get_counts(player).get(job, 0)) >= 1


def set_path(player: Player, path: str) -> str:
    from services.economy import WorkError

    if path not in PATHS:
        raise WorkError("Неизвестный путь.")
    info = PATHS[path]
    job = info["job"]
    if not can_choose_path(player, job):
        title = config.JOBS.get(job, {}).get("title", job)
        raise WorkError(
            f"Путь для {title} откроется с ранга «ученик» "
            f"(несколько смен на этой работе)."
        )
    player.work_path = path
    return (
        f"Путь выбран: {info['label']} — {info['desc']} "
        f"(+{int(config.WORK_PATH_BONUS * 100)}%)."
    )


def path_bonus(player: Player, job: str) -> float:
    p = (getattr(player, "work_path", None) or "").strip()
    info = PATHS.get(p)
    if not info or info["job"] != job:
        return 0.0
    return float(config.WORK_PATH_BONUS)
