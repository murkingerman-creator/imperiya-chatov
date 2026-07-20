"""Учёт личного налога в казну за неделю МСК."""

from __future__ import annotations

from datetime import timedelta, timezone

from db.models import Player
from services.player import utcnow

MSK = timezone(timedelta(hours=3))


def week_key_msk() -> str:
    return utcnow().astimezone(MSK).strftime("%Y-W%W")


def ensure_tax_week(player: Player) -> None:
    key = week_key_msk()
    if (player.tax_week_key or "") != key:
        player.tax_week_key = key
        player.tax_paid_week = 0


def add_tax_paid(player: Player, amount: int) -> None:
    if amount <= 0:
        return
    ensure_tax_week(player)
    player.tax_paid_week = int(player.tax_paid_week or 0) + int(amount)


def tax_paid_display(player: Player) -> int:
    ensure_tax_week(player)
    return int(player.tax_paid_week or 0)
