"""Активация ручных зарядов легенд/мифов."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from bot import config
from db.models import Player
from services.item_effects import get_loadout, try_consume_charge
from services.player import utcnow


class ChargeError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


MANUAL_CHARGES = {
    "reset_job_cds": "Сброс КД работ и контрабанды",
    "treasury_convert": "Перелить до 500 крон в казну ×1.5",
    "tax_override_week": "Сменить налог страны вне КД (лидер)",
}


async def activate_manual_charge(
    session: AsyncSession, player: Player, code: str, *, tax_rate: float | None = None
) -> str:
    if code not in MANUAL_CHARGES:
        raise ChargeError("Этот заряд активируется сам по ситуации.")

    loadout = await get_loadout(session, player)
    if code not in loadout.charges_ready:
        raise ChargeError("Заряд не готов или предмет не экипирован.")

    if code == "reset_job_cds":
        name = await try_consume_charge(session, player, code, loadout)
        player.last_mine_at = None
        player.last_market_at = None
        player.last_guard_at = None
        player.last_smuggle_at = None
        player.last_work_at = None
        await session.commit()
        return f"⚡ {name}: все КД работ сброшены!"

    if code == "treasury_convert":
        if not player.nation:
            raise ChargeError("Нужна страна.")
        amount = min(500, player.crowns)
        if amount < 50:
            raise ChargeError("Нужно хотя бы 50 крон.")
        name = await try_consume_charge(session, player, code, loadout)
        player.crowns -= amount
        gained = int(amount * 1.5)
        player.nation.treasury += gained
        await session.commit()
        return f"⚡ {name}: −{amount} крон → +{gained} в казну"

    if code == "tax_override_week":
        if not player.nation or player.nation.leader_id != player.vk_id:
            raise ChargeError("Только лидер.")
        if tax_rate is None or tax_rate not in config.TAX_PRESETS:
            raise ChargeError("Укажи налог: 5/10/15/20%.")
        name = await try_consume_charge(session, player, code, loadout)
        player.nation.tax_rate = tax_rate
        player.nation.customized_at = utcnow()
        await session.commit()
        return f"⚡ {name}: налог страны = {int(tax_rate*100)}%"

    raise ChargeError("Неизвестный заряд.")
