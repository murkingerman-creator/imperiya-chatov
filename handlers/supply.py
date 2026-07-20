"""Имперский привоз — UI."""

from vkbottle.bot import Bot, Message

from bot.keyboards import jobs_keyboard, supply_keyboard
from db.database import SessionLocal
from handlers.common import reply, resolve_name
from handlers.rules import match_cmd, payload_cmd
from services.player import get_or_create_player
from services.supply import (
    SupplyError,
    buy_supply,
    format_supply_list,
    get_bought,
    get_wave_id,
    list_supply,
)


def register(bot: Bot) -> None:
    @bot.on.message(
        func=match_cmd("supply", "привоз", "📦 привоз", "имперский привоз")
    )
    async def supply_menu(message: Message):
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            data = await list_supply(session)
            wave = data.get("wave_id") or await get_wave_id(session)
            bought = await get_bought(session, wave, player.vk_id)
            await reply(
                message,
                format_supply_list(data, bought=bought),
                keyboard=supply_keyboard(data["stock"]).get_json(),
            )

    @bot.on.message(func=payload_cmd("supply_buy"))
    async def supply_buy(message: Message):
        payload = message.get_payload_json() or {}
        item_id = str(payload.get("item") or "")
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            try:
                result = await buy_supply(session, player, item_id)
            except SupplyError as e:
                data = await list_supply(session)
                await reply(
                    message,
                    e.message,
                    keyboard=supply_keyboard(data["stock"]).get_json(),
                )
                return
            it = result["item"]
            data = await list_supply(session)
            await reply(
                message,
                f"✅ Куплен {it['name']} за {result['price']}🪙\n"
                f"Прочность {result['durability']}/{result['durability']}. "
                f"Экипируй в слот инструмента или держи в сумке.\n"
                f"Баланс: {result['crowns']}🪙 · на складе ещё {result['left']}",
                keyboard=supply_keyboard(data["stock"]).get_json(),
            )
