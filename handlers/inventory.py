from vkbottle.bot import Bot, Message

from bot.keyboards import (
    bag_items_keyboard,
    bag_keyboard,
    charge_activate_keyboard,
    item_actions_keyboard,
    main_keyboard,
    unequip_keyboard,
)
from data import items_catalog as cat
from db.database import SessionLocal
from handlers.common import resolve_name
from handlers.rules import match_cmd, payload_cmd
from services.charges import MANUAL_CHARGES, ChargeError, activate_manual_charge
from services.chronicle_store import add_event
from services.inventory import (
    InventoryError,
    discovered_count,
    donate_item,
    equip,
    get_equipped,
    list_bag,
    merge_commons,
    sell_item,
    unequip,
)
from services.item_effects import format_loadout_short, get_loadout
from services.notify import post_wall
from services.player import get_or_create_player

PAGE_SIZE = 6


def register(bot: Bot) -> None:
    @bot.on.message(func=match_cmd("bag", "сумка", "🎒 сумка", "инвентарь", "арсенал"))
    async def bag_menu(message: Message):
        payload = message.get_payload_json() or {}
        page = int(payload.get("page") or 0)
        await _show_bag(message, page)

    @bot.on.message(func=match_cmd("bag_eq", "экипировка", "🛡 экипировка"))
    async def bag_eq(message: Message):
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            loadout = await get_loadout(session, player)
            lines = ["🛡 Экипировка:", format_loadout_short(loadout)]
            if loadout.charges_ready:
                lines.append("Заряды готовы: " + ", ".join(loadout.charges_ready.keys()))
            await message.answer(
                "\n".join(lines),
                keyboard=unequip_keyboard().get_json(),
            )

    @bot.on.message(func=match_cmd("codex", "кодекс", "📖 кодекс"))
    async def codex(message: Message):
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            n = await discovered_count(session, player.vk_id)
            total = cat.catalog_size()
            await message.answer(
                f"📖 Кодекс Арсенала: {n}/{total}\n"
                "Новые предметы открываются при дропе.",
                keyboard=bag_keyboard().get_json(),
            )

    @bot.on.message(func=payload_cmd("bag_item"))
    async def bag_item(message: Message):
        payload = message.get_payload_json() or {}
        item_id = str(payload.get("id") or "")
        it = cat.get_item(item_id)
        if not it:
            await message.answer("Предмет не найден.")
            return
        await message.answer(
            f"{cat.format_item(it)}\n{cat.format_buffs(it)}",
            keyboard=item_actions_keyboard(item_id, it["rarity"]).get_json(),
        )

    @bot.on.message(func=payload_cmd("bag_equip"))
    async def bag_equip(message: Message):
        payload = message.get_payload_json() or {}
        item_id = str(payload.get("id") or "")
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            try:
                result = await equip(session, player, item_id)
            except InventoryError as e:
                await message.answer(e.message, keyboard=bag_keyboard().get_json())
                return
            text = f"Надето: {cat.format_item(result['item'])}"
            if result.get("mythic_announce"):
                announce = (
                    f"🟥 МИФИЧЕСКИЙ артефакт экипирован!\n"
                    f"{player.name}: {result['item']['name']}"
                )
                await add_event(session, "mythic", announce, str(player.nation_id or ""))
                await post_wall(message.ctx_api, announce)
                text += "\n" + announce
            await message.answer(text, keyboard=bag_keyboard().get_json())

    @bot.on.message(func=payload_cmd("bag_unequip"))
    async def bag_unequip(message: Message):
        payload = message.get_payload_json() or {}
        slot = str(payload.get("slot") or "")
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            try:
                result = await unequip(session, player, slot)
            except InventoryError as e:
                await message.answer(e.message, keyboard=bag_keyboard().get_json())
                return
            it = result["item"]
            label = cat.format_item(it) if it else slot
            await message.answer(f"Снято: {label}", keyboard=bag_keyboard().get_json())

    @bot.on.message(func=payload_cmd("bag_sell"))
    async def bag_sell(message: Message):
        payload = message.get_payload_json() or {}
        item_id = str(payload.get("id") or "")
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            try:
                result = await sell_item(session, player, item_id, 1)
            except InventoryError as e:
                await message.answer(e.message, keyboard=bag_keyboard().get_json())
                return
            await message.answer(
                f"Продано: {cat.format_item(result['item'])} → +{result['price']}\n"
                f"💰 {result['crowns']}",
                keyboard=bag_keyboard().get_json(),
            )

    @bot.on.message(func=payload_cmd("bag_donate"))
    async def bag_donate(message: Message):
        payload = message.get_payload_json() or {}
        item_id = str(payload.get("id") or "")
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            try:
                result = await donate_item(session, player, item_id)
            except InventoryError as e:
                await message.answer(e.message, keyboard=bag_keyboard().get_json())
                return
            await message.answer(
                f"🏛 В казну: {cat.format_item(result['item'])} → +{result['amount']}\n"
                f"Казна: {result['treasury']}",
                keyboard=bag_keyboard().get_json(),
            )

    @bot.on.message(func=payload_cmd("bag_merge"))
    async def bag_merge(message: Message):
        payload = message.get_payload_json() or {}
        item_id = str(payload.get("id") or "")
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            try:
                result = await merge_commons(session, player, item_id)
            except InventoryError as e:
                await message.answer(e.message, keyboard=bag_keyboard().get_json())
                return
            await message.answer(
                f"🔀 Слито {result['spent']}× {result['from']['name']}\n"
                f"→ {cat.format_item(result['to'])}",
                keyboard=bag_keyboard().get_json(),
            )

    @bot.on.message(func=match_cmd("bag_charges", "заряды", "⚡ заряды"))
    async def bag_charges(message: Message):
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            loadout = await get_loadout(session, player)
            ready = [c for c in loadout.charges_ready if c in MANUAL_CHARGES]
            if not ready:
                await message.answer(
                    "Нет ручных зарядов (нужен экипированный миф/легенда с ручной активацией).",
                    keyboard=bag_keyboard().get_json(),
                )
                return
            lines = ["⚡ Готовые ручные заряды:"]
            for c in ready:
                lines.append(f"• {MANUAL_CHARGES[c]}")
            await message.answer(
                "\n".join(lines),
                keyboard=charge_activate_keyboard(ready).get_json(),
            )

    @bot.on.message(func=payload_cmd("bag_charge"))
    async def bag_charge_activate(message: Message):
        payload = message.get_payload_json() or {}
        code = str(payload.get("code") or "")
        tax = payload.get("tax")
        tax_rate = float(tax) if tax is not None else None
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            try:
                text = await activate_manual_charge(
                    session, player, code, tax_rate=tax_rate
                )
            except ChargeError as e:
                await message.answer(e.message, keyboard=bag_keyboard().get_json())
                return
            await message.answer(text, keyboard=bag_keyboard().get_json())


async def _show_bag(message: Message, page: int) -> None:
    name = await resolve_name(message)
    async with SessionLocal() as session:
        player = await get_or_create_player(session, message.from_id, name)
        bag = await list_bag(session, player.vk_id)
        equipped = await get_equipped(session, player.vk_id)
        n = await discovered_count(session, player.vk_id)
        total = cat.catalog_size()

        start = max(0, page * PAGE_SIZE)
        chunk = bag[start : start + PAGE_SIZE]
        has_next = start + PAGE_SIZE < len(bag)

        eq_line = (
            ", ".join(cat.format_item(it) for it in equipped.values())
            if equipped
            else "пусто"
        )
        lines = [
            f"🎒 Сумка ({len(bag)} стаков) · Кодекс {n}/{total}",
            f"Экип: {eq_line}",
            "",
        ]
        if not chunk:
            lines.append("Пусто. Работай — предметы падают с шансом.")
            await message.answer("\n".join(lines), keyboard=bag_keyboard(page).get_json())
            return

        for it, qty in chunk:
            lines.append(f"• {cat.format_item(it)} ×{qty}")
        lines.append("\nНажми предмет ниже для действий.")
        await message.answer(
            "\n".join(lines),
            keyboard=bag_items_keyboard(chunk, page, has_next).get_json(),
        )
