import random
import secrets
from dataclasses import dataclass, field

from bot import config
from services.player import utcnow


@dataclass
class Duel:
    token: str
    peer_id: int
    challenger_id: int
    challenger_name: str
    opponent_id: int | None
    bet: int
    mode: str  # rps | number
    expires_at: float
    challenger_move: str | None = None
    opponent_move: str | None = None
    secret_number: int | None = None


_duels: dict[str, Duel] = {}


def create_duel(peer_id: int, challenger_id: int, name: str, bet: int, mode: str) -> Duel:
    if bet < config.DUEL_MIN_BET or bet > config.DUEL_MAX_BET:
        raise ValueError(f"Ставка {config.DUEL_MIN_BET}–{config.DUEL_MAX_BET}")
    if mode not in {"rps", "number"}:
        raise ValueError("Режим: rps или number")
    token = secrets.token_hex(3)
    duel = Duel(
        token=token,
        peer_id=peer_id,
        challenger_id=challenger_id,
        challenger_name=name,
        opponent_id=None,
        bet=bet,
        mode=mode,
        expires_at=utcnow().timestamp() + config.DUEL_TTL_SEC,
        secret_number=random.randint(1, 5) if mode == "number" else None,
    )
    _duels[token] = duel
    return duel


def get_duel(token: str) -> Duel | None:
    d = _duels.get(token)
    if not d:
        return None
    if utcnow().timestamp() > d.expires_at:
        _duels.pop(token, None)
        return None
    return d


def rps_winner(a: str, b: str) -> int:
    """1 if a wins, 2 if b, 0 draw."""
    if a == b:
        return 0
    wins = {("rock", "scissors"), ("scissors", "paper"), ("paper", "rock")}
    return 1 if (a, b) in wins else 2


def number_winner(a: int, b: int, secret: int) -> int:
    """1 if a closer, 2 if b, 0 draw."""
    da, db = abs(a - secret), abs(b - secret)
    if da == db:
        return 0
    return 1 if da < db else 2


RPS_LABEL = {"rock": "✊ камень", "paper": "✋ бумага", "scissors": "✌ ножницы"}


def cleanup_duel(token: str) -> None:
    _duels.pop(token, None)

