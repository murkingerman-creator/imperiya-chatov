from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from bot import config
from db.models import Nation, Player
from services.player import ensure_aware, utcnow


class CustomizeError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def _require_leader(player: Player) -> Nation:
    if not player.nation_id or not player.nation:
        raise CustomizeError("Сначала вступи в страну.")
    if player.nation.leader_id != player.vk_id:
        raise CustomizeError("Оформлять страну может только лидер.")
    return player.nation


async def _pay_if_needed(session: AsyncSession, player: Player, nation: Nation) -> int:
    """Возвращает списанную стоимость (0 или CUSTOMIZE_CHANGE_COST)."""
    last = ensure_aware(nation.customized_at)
    now = utcnow()
    if last and now < last + timedelta(hours=config.CUSTOMIZE_COOLDOWN_HOURS):
        if player.crowns < config.CUSTOMIZE_CHANGE_COST:
            raise CustomizeError(
                f"Частая смена оформления стоит {config.CUSTOMIZE_CHANGE_COST} крон."
            )
        player.crowns -= config.CUSTOMIZE_CHANGE_COST
        return config.CUSTOMIZE_CHANGE_COST
    return 0


async def set_field(
    session: AsyncSession,
    player: Player,
    field: str,
    value: str,
) -> dict:
    nation = _require_leader(player)
    value = (value or "").strip()

    limits = {
        "motto": 120,
        "capital": 64,
        "anthem": 120,
        "laws": 200,
        "welcome": 120,
    }
    if field in limits:
        if not value:
            raise CustomizeError("Пустое значение нельзя.")
        if len(value) > limits[field]:
            raise CustomizeError(f"Слишком длинно (макс {limits[field]}).")
        cost = await _pay_if_needed(session, player, nation)
        setattr(nation, field, value)
    elif field == "flag_emoji":
        if value not in config.FLAGS:
            raise CustomizeError("Выбери флаг из списка.")
        cost = await _pay_if_needed(session, player, nation)
        nation.flag_emoji = value
    elif field == "emblem_emoji":
        if value not in config.EMBLEMS:
            raise CustomizeError("Выбери герб из списка.")
        cost = await _pay_if_needed(session, player, nation)
        nation.emblem_emoji = value
    elif field == "government":
        if value not in config.GOVERNMENTS:
            raise CustomizeError("Неизвестная форма правления.")
        cost = await _pay_if_needed(session, player, nation)
        nation.government = value
    elif field == "color_tag":
        if value not in config.COLORS:
            raise CustomizeError("Неизвестный цвет.")
        cost = await _pay_if_needed(session, player, nation)
        nation.color_tag = value
    elif field == "tax_rate":
        try:
            rate = float(value)
        except ValueError as e:
            raise CustomizeError("Неверный налог.") from e
        if rate not in config.TAX_PRESETS:
            raise CustomizeError("Налог: 5 / 10 / 15 / 20%.")
        cost = await _pay_if_needed(session, player, nation)
        nation.tax_rate = rate
    else:
        raise CustomizeError("Неизвестное поле.")

    nation.customized_at = utcnow()
    await session.commit()
    return {"nation": nation, "cost": cost, "crowns": player.crowns}
