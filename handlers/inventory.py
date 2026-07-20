from vkbottle.bot import Bot, Message

from bot.keyboards import (
    bag_items_keyboard,
    bag_keyboard,
    charge_activate_keyboard,
    confirm_junk_sell_keyboard,
    confirm_sell_bot_keyboard,
    item_actions_keyboard,
    main_keyboard,
    unequip_keyboard,
)
from content import items_catalog as cat
from db.database import SessionLocal
from handlers.common import reply, resolve_name
from handlers.rules import match_cmd, payload_cmd
from services.charges import MANUAL_CHARGES, ChargeError, activate_manual_charge
from services.chronicle_store import add_event
from services.inventory import (
    InventoryError,
    bag_qty,
    discovered_count,
    donate_item,
    equip,
    get_equipped,
    list_bag,
    merge_commons,
    preview_junk_sale,
    preview_sell_price,
    sell_item,
    sell_junk,
    unbound_qty,
    unequip,
    upgrade_equipped,
)
from services.item_effects import format_loadout_short, get_loadout
from services.announce import announce_nation
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
            await reply(message, 
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
            await reply(message, 
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
        await reply(message, 
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
                await reply(message, e.message, keyboard=bag_keyboard().get_json())
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
            await reply(message, text, keyboard=bag_keyboard().get_json())

    @bot.on.message(func=payload_cmd("bag_upgrade"))
    async def bag_upgrade(message: Message):
        payload = message.get_payload_json() or {}
        item_id = str(payload.get("id") or "")
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            try:
                result = await upgrade_equipped(session, player, item_id)
            except InventoryError as e:
                await reply(message, e.message, keyboard=bag_keyboard().get_json())
                return
            it = result["item"]
            text = (
                f"⚒ Заточка +{result['upgrade']}!\n"
                f"{cat.format_item(it) if it else item_id}\n"
                f"−{result['cost']} крон · 💰 {result['crowns']}"
            )
            await announce_nation(
                message.ctx_api,
                player.nation,
                f"⚒ {player.name}: заточка +{result['upgrade']} "
                f"({it['name'] if it else item_id})",
            )
            await reply(message, text, keyboard=bag_keyboard().get_json())

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
                await reply(message, e.message, keyboard=bag_keyboard().get_json())
                return
            it = result["item"]
            label = cat.format_item(it) if it else slot
            await reply(message, f"Снято: {label}", keyboard=bag_keyboard().get_json())

    @bot.on.message(func=payload_cmd("bag_sell"))
    async def bag_sell(message: Message):
        payload = message.get_payload_json() or {}
        item_id = str(payload.get("id") or "")
        it = cat.get_item(item_id)
        if not it:
            await reply(message, "Предмет не найден.", keyboard=bag_keyboard().get_json())
            return
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            try:
                qty_all = await bag_qty(session, player.vk_id, item_id)
                if qty_all < 1:
                    raise InventoryError("Нет такого в сумке.")
                one = await preview_sell_price(session, player, item_id, 1)
                all_p = (
                    await preview_sell_price(session, player, item_id, qty_all)
                    if qty_all > 1
                    else one
                )
            except InventoryError as e:
                await reply(message, e.message, keyboard=bag_keyboard().get_json())
                return
        hint = ""
        if one.get("bound_sold"):
            hint = " (есть трофеи колеса — уценка)"
        await reply(
            message,
            f"💰 Продажа боту\n"
            f"{cat.format_item(it)} × до {qty_all}\n"
            f"×1 → {one['price']} крон · все → {all_p['price']} крон{hint}\n\n"
            f"Сколько продать?",
            keyboard=confirm_sell_bot_keyboard(
                item_id, one["price"], qty_all, all_p["price"]
            ).get_json(),
        )

    @bot.on.message(func=payload_cmd("bag_sell_confirm"))
    async def bag_sell_confirm(message: Message):
        payload = message.get_payload_json() or {}
        item_id = str(payload.get("id") or "")
        raw_qty = payload.get("qty", 1)
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            try:
                if raw_qty == "all" or str(raw_qty) == "all":
                    qty = await bag_qty(session, player.vk_id, item_id)
                else:
                    qty = max(1, int(raw_qty or 1))
                result = await sell_item(session, player, item_id, qty)
            except InventoryError as e:
                await reply(message, e.message, keyboard=bag_keyboard().get_json())
                return
            note = ""
            if result.get("bound_sold"):
                note = " (трофей колеса, уценка)"
            await reply(
                message,
                f"Продано: {cat.format_item(result['item'])} ×{result['qty']} "
                f"→ +{result['price']}{note}\n💰 {result['crowns']}",
                keyboard=bag_keyboard().get_json(),
            )

    @bot.on.message(func=payload_cmd("bag_junk"))
    async def bag_junk(message: Message):
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            preview = await preview_junk_sale(session, player)
        if preview["qty"] <= 0:
            await reply(
                message,
                "🧹 Нечего сливать.\n"
                "Сливаются только unbound ordinary/необычные (не экип, не rare+).",
                keyboard=bag_keyboard().get_json(),
            )
            return
        sample = "\n".join(preview["lines"][:8])
        more = ""
        if len(preview["lines"]) > 8:
            more = f"\n… и ещё {len(preview['lines']) - 8}"
        await reply(
            message,
            f"🧹 Слить хлам (common/uncommon, без трофеев колеса)\n"
            f"{sample}{more}\n\n"
            f"Итого: {preview['qty']} шт. → ~{preview['price']} крон\n"
            f"Rare+ и экип не трогаем.",
            keyboard=confirm_junk_sell_keyboard(
                preview["price"], preview["qty"]
            ).get_json(),
        )

    @bot.on.message(func=payload_cmd("bag_junk_confirm"))
    async def bag_junk_confirm(message: Message):
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            try:
                result = await sell_junk(session, player)
            except InventoryError as e:
                await reply(message, e.message, keyboard=bag_keyboard().get_json())
                return
            await reply(
                message,
                f"🧹 Слито {result['qty']} шт. → +{result['price']}\n"
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
                await reply(message, e.message, keyboard=bag_keyboard().get_json())
                return
            await reply(message, 
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
                await reply(message, e.message, keyboard=bag_keyboard().get_json())
                return
            await reply(message, 
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
                await reply(message, 
                    "Нет ручных зарядов (нужен экипированный миф/легенда с ручной активацией).",
                    keyboard=bag_keyboard().get_json(),
                )
                return
            lines = ["⚡ Готовые ручные заряды:"]
            for c in ready:
                lines.append(f"• {MANUAL_CHARGES[c]}")
            await reply(message, 
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
                await reply(message, e.message, keyboard=bag_keyboard().get_json())
                return
            await reply(message, text, keyboard=bag_keyboard().get_json())


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
            await reply(message, "\n".join(lines), keyboard=bag_keyboard(page).get_json())
            return

        for it, qty in chunk:
            lines.append(f"• {cat.format_item(it)} ×{qty}")
        lines.append("\nНажми предмет ниже для действий.")
        await reply(message, 
            "\n".join(lines),
            keyboard=bag_items_keyboard(chunk, page, has_next).get_json(),
        )
