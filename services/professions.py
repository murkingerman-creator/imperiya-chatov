"""Ранги профессий: счётчик работ → бонус к доходу этой работы."""

from __future__ import annotations

from bot import config
from db.models import Player


def parse_job_counts(raw: str | None) -> dict[str, int]:
    out: dict[str, int] = {}
    for part in (raw or "").split(","):
        part = part.strip()
        if not part or "=" not in part:
            continue
        job, _, num = part.partition("=")
        job = job.strip()
        try:
            out[job] = max(0, int(num))
        except ValueError:
            continue
    return out


def dump_job_counts(counts: dict[str, int]) -> str:
    parts = [f"{k}={v}" for k, v in sorted(counts.items()) if v > 0]
    return ",".join(parts)[:480]


def job_rank(count: int) -> int:
    """0..len(thresholds)-1"""
    rank = 0
    for i, need in enumerate(config.JOB_RANK_THRESHOLDS):
        if count >= need:
            rank = i
    return rank


def rank_name(rank: int) -> str:
    names = config.JOB_RANK_NAMES
    if rank < 0:
        return names[0]
    if rank >= len(names):
        return names[-1]
    return names[rank]


def rank_bonus(rank: int) -> float:
    if rank <= 0:
        return 0.0
    return float(config.JOB_RANK_BONUS) * rank


def get_counts(player: Player) -> dict[str, int]:
    return parse_job_counts(getattr(player, "job_counts", None) or "")


def bump_job(player: Player, job: str) -> dict:
    """+1 к счётчику. Возвращает info о ранге."""
    counts = get_counts(player)
    before = counts.get(job, 0)
    counts[job] = before + 1
    player.job_counts = dump_job_counts(counts)
    old_r = job_rank(before)
    new_r = job_rank(counts[job])
    title = config.JOBS.get(job, {}).get("title", job)
    note = None
    if new_r > old_r:
        note = (
            f"🏅 {title}: ранг «{rank_name(new_r)}» "
            f"(+{int(rank_bonus(new_r) * 100)}% к этой работе)"
        )
    return {
        "count": counts[job],
        "rank": new_r,
        "rank_name": rank_name(new_r),
        "bonus": rank_bonus(new_r),
        "note": note,
    }


def work_bonus_for(player: Player, job: str) -> float:
    return rank_bonus(job_rank(get_counts(player).get(job, 0)))


def format_professions_line(player: Player) -> str:
    counts = get_counts(player)
    if not counts:
        return "Профессии: пока нет рангов — работай."
    bits = []
    for job, n in sorted(counts.items(), key=lambda x: -x[1])[:5]:
        title = config.JOBS.get(job, {}).get("title", job)
        r = job_rank(n)
        bits.append(f"{title} {rank_name(r)} ({n})")
    return "Профессии: " + " · ".join(bits)
