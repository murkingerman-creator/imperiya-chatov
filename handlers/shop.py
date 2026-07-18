"""Имперская лавка и выкуп из тюрьмы."""

from vkbottle.bot import Bot, Message

from bot.keyboards import main_keyboard, shop_keyboard
from bot import config
from db.database import SessionLocal
from handlers.common import reply, resolve_name
from handlers.rules import match_cmd, payload_cmd, text_in
from services.player import get_or_create_player, regenerate_energy
from services.shop import (
    ShopError,
    bail_cost,
    buy_bail,
    buy_energy_full,
    buy_raid_bless,
    buy_treasury_gift,
    buy_wheel,
    buy_work_luck,
    jail_minutes_left,
    shop_catalog_text,
)
from services.announce import announce_nation


def _bail_text(message: Message) -> bool:
    if (message.get_payload_json() or {}).get("cmd"):
        return False
    return text_in("выкуп", "🔓 выкуп", "bail")(message)


def register(bot: Bot) -> None:
    @bot.on.message(
        func=match_cmd("shop", "лавка", "🏪 лавка", "магазин")
    )
    async def shop_menu(message: Message):
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            regenerate_energy(player)
            await session.commit()
            await reply(
                message,
                shop_catalog_text(player),
                keyboard=shop_keyboard(jailed=jail_minutes_left(player) > 0).get_json(),
            )

    @bot.on.message(func=_bail_text)
    async def bail_text(message: Message):
        await _do_buy(message, "bail")

    @bot.on.message(func=payload_cmd("shop_buy"))
    async def shop_buy(message: Message):
        payload = message.get_payload_json() or {}
        item = str(payload.get("item") or "")
        await _do_buy(message, item)


async def _do_buy(message: Message, item: str) -> None:
    name = await resolve_name(message)
    async with SessionLocal() as session:
        player = await get_or_create_player(session, message.from_id, name)
        try:
            if item == "bail":
                result = await buy_bail(session, player)
                text = (
                    f"🔓 Выкуплен за {result['cost']} крон!\n"
                    f"Свобода (~{result['freed_min']} мин срока снято).\n"
                    f"💰 {result['crowns']}"
                )
                await announce_nation(
                    message.ctx_api,
                    player.nation,
                    f"🔓 {player.name} выкупился из тюрьмы (−{result['cost']})",
                )
            elif item == "energy":
                result = await buy_energy_full(session, player)
                text = (
                    f"⚡ Эликсир выпит (−{result['cost']}).\n"
                    f"Энергия: {result['energy']}\n"
                    f"💰 {result['crowns']}"
                )
            elif item == "work_luck":
                result = await buy_work_luck(session, player)
                text = (
                    f"🍀 Печать удачи (−{result['cost']}).\n"
                    f"+{result['bonus_pct']}% к работам ×{result['stacks']}.\n"
                    f"💰 {result['crowns']}"
                )
            elif item == "treasury":
                result = await buy_treasury_gift(session, player)
                text = (
                    f"🏛 Вклад в {result['nation']} (−{result['cost']}).\n"
                    f"Казна теперь: {result['treasury']}\n"
                    f"💰 {result['crowns']}"
                )
            elif item == "raid_bless":
                result = await buy_raid_bless(session, player)
                text = (
                    f"⚔ Знамя рейда (−{result['cost']}).\n"
                    f"+{result['bonus_pct']}% к шансу следующего рейда.\n"
                    f"💰 {result['crowns']}"
                )
            elif item == "wheel":
                result = await buy_wheel(session, player)
                if result["type"] == "empty":
                    text = (
                        f"🎰 Колесо (−{result['cost']})…\n"
                        f"Ничего. Империя улыбнулась.\n"
                        f"💰 {result['crowns']}"
                    )
                elif result["type"] == "crowns":
                    text = (
                        f"🎰 Колесо (−{result['cost']})!\n"
                        f"+{result['amount']} крон\n💰 {result['crowns']}"
                    )
                else:
                    it = result["item"]
                    cut = int((1 - config.SHOP_WHEEL_SELL_MULT) * 100)
                    text = (
                        f"🎰 Колесо (−{result['cost']})!\n"
                        f"✨ {it.get('emoji', '')} {it['name']} ({it['rarity']})\n"
                        f"⛓ Трофей колеса: выкуп у бота −{cut}% (на торг — как хочешь).\n"
                        f"💰 {result['crowns']}"
                    )
                    if it.get("rarity") in ("rare", "epic", "legendary", "mythic"):
                        await announce_nation(
                            message.ctx_api,
                            player.nation,
                            f"🎰 {player.name} выбил {it.get('emoji', '')} {it['name']}!",
                        )
            else:
                await reply(
                    message,
                    "Неизвестный товар. Открой 🏪 Лавка.",
                    keyboard=main_keyboard().get_json(),
                )
                return
        except ShopError as e:
            await reply(
                message,
                e.message,
                keyboard=shop_keyboard(
                    jailed=bail_cost(player) is not None
                ).get_json(),
            )
            return

        await reply(
            message,
            text,
            keyboard=shop_keyboard(jailed=jail_minutes_left(player) > 0).get_json(),
        )
