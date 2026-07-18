"""Чёрный рынок по пятницам."""

from __future__ import annotations

from datetime import timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from bot import config
from db.models import Player
from services.flash_events import get_flash_event
from services.item_effects import set_buff
from services.player import regenerate_energy, utcnow
from services.shop import ShopError

MSK = timezone(timedelta(hours=3))


def is_black_market_open(flash: dict | None = None) -> bool:
    now = utcnow().astimezone(MSK)
    if now.weekday() == 4 and 18 <= now.hour < 20:
        return True
    if flash and flash.get("key") == "black_market":
        return True
    return False


async def black_market_text(session: AsyncSession) -> str:
    flash = await get_flash_event(session)
    if not is_black_market_open(flash):
        return (
            "🕶 Чёрный рынок закрыт.\n"
            "Открыт по пятницам 18–20 МСК или во вспышку «чёрный рынок»."
        )
    lines = ["🕶 Чёрный рынок (2ч / вспышка)", "Безумные цены — бери быстро:", ""]
    for s in config.BLACK_MARKET_SLOTS:
        lines.append(f"• {s['name']} — {s['cost']}💰 (`{s['id']}`)")
    lines.append("")
    lines.append("Кнопка ниже или: чр bm_energy")
    return "\n".join(lines)


async def buy_black(session: AsyncSession, player: Player, slot_id: str) -> str:
    flash = await get_flash_event(session)
    if not is_black_market_open(flash):
        raise ShopError("Чёрный рынок сейчас закрыт.")
    slot = next((s for s in config.BLACK_MARKET_SLOTS if s["id"] == slot_id), None)
    if not slot:
        raise ShopError("Нет такого слота.")
    cost = int(slot["cost"])
    if player.crowns < cost:
        raise ShopError(f"Нужно {cost} крон.")
    player.crowns -= cost
    kind = slot["kind"]
    if kind == "energy":
        regenerate_energy(player)
        player.energy = config.MAX_ENERGY
        await session.commit()
        return f"🕶 Куплено: {slot['name']} (−{cost}). Энергия полная!"
    if kind == "work_luck":
        await set_buff(session, player.vk_id, "work_luck", 3)
        await session.commit()
        return f"🕶 Куплено: {slot['name']} (−{cost}). Удача на 3 работы!"
    if kind == "raid_bless":
        await set_buff(session, player.vk_id, "raid_bless", 1)
        await session.commit()
        return f"🕶 Куплено: {slot['name']} (−{cost}). Знамя на следующий рейд!"
    if kind == "wheel":
        from services.shop import buy_wheel

        # уже списали cost слота — вернём, buy_wheel спишет ту же сумму
        player.crowns += cost
        result = await buy_wheel(session, player, cost=cost)
        if result["type"] == "empty":
            body = "пусто… империя забрала ставку"
        elif result["type"] == "crowns":
            body = f"+{result['amount']} крон"
        else:
            it = result["item"]
            body = (
                f"{it.get('emoji', '')} {it['name']} ({it['rarity']}) "
                f"— трофей колеса (−{int((1 - config.SHOP_WHEEL_SELL_MULT) * 100)}% выкуп)"
            )
        return (
            f"🕶 Колесо бездны (−{cost})!\n{body}\n"
            f"💰 {result['crowns']}"
        )
    raise ShopError("Слот сломан.")
