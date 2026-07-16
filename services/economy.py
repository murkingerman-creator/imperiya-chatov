import random
import secrets
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from bot import config
from db.models import Player
from services.player import ensure_aware, regenerate_energy, utcnow


class WorkError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


@dataclass
class MiniSession:
    vk_id: int
    job: str
    token: str
    correct: str
    expires_at: float
    meta: dict


_sessions: dict[str, MiniSession] = {}


def _job_last_attr(job: str) -> str:
    return {"mine": "last_mine_at", "market": "last_market_at", "guard": "last_guard_at"}[job]


def check_can_start_job(player: Player, job: str) -> dict:
    if job not in config.JOBS:
        raise WorkError("Неизвестная работа.")
    regenerate_energy(player)
    spec = config.JOBS[job]
    now = utcnow()
    last = ensure_aware(getattr(player, _job_last_attr(job)))
    if last:
        ready_at = last + timedelta(minutes=spec["cooldown_min"])
        if now < ready_at:
            minutes_left = int((ready_at - now).total_seconds() / 60) + 1
            raise WorkError(
                f"{spec['title']}: кулдаун. Подожди ещё ~{minutes_left} мин."
            )
    if player.energy < 1:
        raise WorkError("Недостаточно энергии.")
    return spec


def start_minigame(player: Player, job: str) -> dict:
    check_can_start_job(player, job)
    token = secrets.token_hex(4)
    now_ts = utcnow().timestamp()

    if job == "mine":
        options = ["A", "B", "C"]
        correct = random.choice(options)
        prompt = (
            "⛏ Шахта: в какой штольне руда?\n"
            "Выбери A / B / C за 60 секунд."
        )
        buttons = [("Штольня A", "A"), ("Штольня B", "B"), ("Штольня C", "C")]
        meta = {}
    elif job == "market":
        rate = random.randint(40, 80)
        correct = random.choice(["up", "down"])
        prompt = (
            f"🛒 Рынок: курс сейчас {rate}.\n"
            "Куда пойдёт цена — выше или ниже?"
        )
        buttons = [("📈 Выше", "up"), ("📉 Ниже", "down")]
        meta = {"rate": rate}
    else:  # guard
        faces = ["🙂", "😎", "🥸"]
        spy_idx = random.randint(0, 2)
        correct = str(spy_idx)
        prompt = (
            "🛡 Охрана: кто шпион?\n"
            f"1) {faces[0]}  2) {faces[1]}  3) {faces[2]}"
        )
        buttons = [
            (f"1 {faces[0]}", "0"),
            (f"2 {faces[1]}", "1"),
            (f"3 {faces[2]}", "2"),
        ]
        meta = {"faces": faces}

    # drop old sessions for user
    for k, s in list(_sessions.items()):
        if s.vk_id == player.vk_id or s.expires_at < now_ts:
            _sessions.pop(k, None)

    _sessions[token] = MiniSession(
        vk_id=player.vk_id,
        job=job,
        token=token,
        correct=correct,
        expires_at=now_ts + 60,
        meta=meta,
    )
    return {"token": token, "prompt": prompt, "buttons": buttons, "job": job}


async def finish_minigame(
    session: AsyncSession, player: Player, token: str, answer: str
) -> dict:
    game = _sessions.pop(token, None)
    if not game or game.vk_id != player.vk_id:
        raise WorkError("Мини-игра не найдена или устарела. Начни работу заново.")
    if utcnow().timestamp() > game.expires_at:
        raise WorkError("Время вышло. Попробуй работу снова.")

    spec = check_can_start_job(player, game.job)
    success = answer == game.correct
    base = random.randint(spec["reward_min"], spec["reward_max"])
    mult = spec["success_mult"] if success else spec["fail_mult"]
    gross = max(1, int(base * mult))

    tax = 0
    nation_name = None
    treasury_bonus = 0
    tax_rate = config.TAX_RATE
    if player.nation_id and player.nation:
        nation_name = player.nation.name
        tax_rate = player.nation.tax_rate or config.TAX_RATE
        tax = max(1, int(gross * tax_rate))
        player.nation.treasury += tax
        if success and game.job == "guard":
            treasury_bonus = int(spec.get("treasury_bonus", 0))
            player.nation.treasury += treasury_bonus

    net = gross - tax
    player.crowns += net
    player.energy -= 1
    now = utcnow()
    setattr(player, _job_last_attr(game.job), now)
    player.last_work_at = now
    player.energy_updated_at = now
    await session.commit()

    return {
        "success": success,
        "job": game.job,
        "title": spec["title"],
        "gross": gross,
        "tax": tax,
        "net": net,
        "crowns": player.crowns,
        "energy": player.energy,
        "nation_name": nation_name,
        "treasury_bonus": treasury_bonus,
        "correct": game.correct,
    }


# legacy helper for smoke tests
async def do_work(session: AsyncSession, player: Player) -> dict:
    """Быстрая работа без мини-игры (совместимость / тесты)."""
    regenerate_energy(player)
    now = utcnow()
    last = ensure_aware(player.last_mine_at or player.last_work_at)
    if last:
        ready_at = last + timedelta(minutes=config.JOBS["mine"]["cooldown_min"])
        if now < ready_at:
            raise WorkError("Кулдаун шахты.")
    if player.energy < 1:
        raise WorkError("Недостаточно энергии.")

    gross = random.randint(45, 90)
    tax = 0
    nation_name = None
    if player.nation_id and player.nation:
        nation_name = player.nation.name
        rate = player.nation.tax_rate or 0.1
        tax = max(1, int(gross * rate))
        player.nation.treasury += tax
    net = gross - tax
    player.crowns += net
    player.energy -= 1
    player.last_mine_at = now
    player.last_work_at = now
    await session.commit()
    return {
        "gross": gross,
        "tax": tax,
        "net": net,
        "crowns": player.crowns,
        "energy": player.energy,
        "nation_name": nation_name,
    }
