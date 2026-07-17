import re

from vkbottle.bot import Bot, Message
from sqlalchemy import select

from bot import config
from bot.keyboards import (
    market_listing_actions_keyboard,
    market_listings_keyboard,
    market_menu_keyboard,
    market_price_keyboard,
)
from content import items_catalog as cat
from db.database import SessionLocal
from db.models import Player
from handlers.common import reply, resolve_name
from handlers.rules import match_cmd, payload_cmd
from services.marketplace import (
    MarketError,
    buy_listing,
    cancel_listing,
    create_listing,
    format_listing_card,
    search_listings,
)
from services.player import get_or_create_player

SEARCH_RE = re.compile(
    r"^(?:найти|поиск|торг\s+поиск)\s+(.+)$",
    re.IGNORECASE,
)
LIST_RE = re.compile(
    r"^(?:торг|выставить)\s+(\S+)\s+(\d+)$",
    re.IGNORECASE,
)


def _is_search(message: Message) -> bool:
    return bool(SEARCH_RE.match((message.text or "").strip()))


def _is_list_text(message: Message) -> bool:
    return bool(LIST_RE.match((message.text or "").strip()))


def register(bot: Bot) -> None:
    @bot.on.message(
        func=match_cmd(
            "market_menu",
            "торг",
            "🛒 торг",
            "барахолка",
            "маркет",
            "площадка",
        )
    )
    async def market_home(message: Message):
        await reply(message, 
            "🛒 Торговая площадка\n"
            "Покупай и продавай любые предметы игрокам.\n"
            f"Комиссия продавца {int(config.MARKET_FEE * 100)}% · "
            f"лот до {config.MARKET_HOURS}ч · макс {config.MARKET_MAX_LISTINGS} лотов.\n\n"
            "Фильтр по редкости кнопками.\n"
            "Поиск: найти кирка / найти сердце\n"
            "Выставить: торг <id> <цена> или из Сумки → На торг",
            keyboard=market_menu_keyboard().get_json(),
        )

    @bot.on.message(func=payload_cmd("market"))
    async def market_browse(message: Message):
        await _browse(message)

    @bot.on.message(func=match_cmd("mkt_help", "🔎 поиск"))
    async def market_help(message: Message):
        await reply(message, 
            "🔎 Поиск на торге\n"
            "• найти <название> — лоты по имени\n"
            "• найти жила — частичное совпадение\n"
            "• кнопки редкости на экране Торг\n"
            "• торг rusty_pick 200 — выставить по id\n\n"
            "В карточке лота — полное описание баффов.",
            keyboard=market_menu_keyboard().get_json(),
        )

    @bot.on.message(func=_is_search)
    async def market_search_text(message: Message):
        m = SEARCH_RE.match((message.text or "").strip())
        if not m:
            return
        query = m.group(1).strip()
        await _browse(message, query=query, page=0)

    @bot.on.message(func=payload_cmd("mkt_view"))
    async def market_view(message: Message):
        payload = message.get_payload_json() or {}
        listing_id = int(payload.get("id") or 0)
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            from db.models import MarketListing

            res = await session.execute(
                select(MarketListing).where(MarketListing.id == listing_id)
            )
            listing = res.scalar_one_or_none()
            if not listing or not listing.active:
                await reply(message, 
                    "Лот не найден.",
                    keyboard=market_menu_keyboard().get_json(),
                )
                return
            seller = await session.execute(
                select(Player).where(Player.vk_id == listing.seller_vk_id)
            )
            s = seller.scalar_one_or_none()
            text = format_listing_card(listing, s.name if s else None)
            await reply(message, 
                text,
                keyboard=market_listing_actions_keyboard(
                    listing.id, is_owner=listing.seller_vk_id == player.vk_id
                ).get_json(),
            )

    @bot.on.message(func=payload_cmd("mkt_buy"))
    async def market_buy(message: Message):
        payload = message.get_payload_json() or {}
        listing_id = int(payload.get("id") or 0)
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            try:
                result = await buy_listing(session, player, listing_id)
            except MarketError as e:
                await reply(message, e.message, keyboard=market_menu_keyboard().get_json())
                return
            it = result["item"]
            first = " (новый в кодексе!)" if result.get("first") else ""
            await reply(message, 
                f"✅ Куплено за {result['price']}💰\n"
                f"{cat.format_item(it)}{first}\n"
                f"{cat.format_buffs(it)}\n"
                f"💰 Твой баланс: {result['buyer_crowns']}",
                keyboard=market_menu_keyboard().get_json(),
            )

    @bot.on.message(func=payload_cmd("mkt_cancel"))
    async def market_cancel(message: Message):
        payload = message.get_payload_json() or {}
        listing_id = int(payload.get("id") or 0)
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            try:
                result = await cancel_listing(session, player, listing_id)
            except MarketError as e:
                await reply(message, e.message, keyboard=market_menu_keyboard().get_json())
                return
            it = result["item"]
            await reply(message, 
                f"Лот снят. {cat.format_item(it) if it else ''} вернулся в сумку.",
                keyboard=market_menu_keyboard().get_json(),
            )

    @bot.on.message(func=match_cmd("mkt_mine", "мои лоты", "📦 мои лоты"))
    async def market_mine(message: Message):
        payload = message.get_payload_json() or {}
        page = int(payload.get("page") or 0)
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            listings, has_next = await search_listings(
                session, seller_vk_id=player.vk_id, page=page
            )
            if not listings and page == 0:
                await reply(message, 
                    "У тебя нет активных лотов.\nИз Сумки → На торг.",
                    keyboard=market_menu_keyboard().get_json(),
                )
                return
            lines = ["📦 Твои лоты:"]
            for listing in listings:
                it = cat.get_item(listing.item_id)
                lines.append(
                    f"#{listing.id} {cat.format_item(it) if it else listing.item_id} "
                    f"— {listing.price}💰"
                )
            await reply(message, 
                "\n".join(lines),
                keyboard=market_listings_keyboard(
                    listings, page=page, has_next=has_next, mine=True
                ).get_json(),
            )

    @bot.on.message(func=payload_cmd("mkt_mine"))
    async def market_mine_payload(message: Message):
        await market_mine(message)

    @bot.on.message(func=payload_cmd("mkt_sell_menu"))
    async def market_sell_menu(message: Message):
        payload = message.get_payload_json() or {}
        item_id = str(payload.get("id") or "")
        it = cat.get_item(item_id)
        if not it:
            await message.answer("Предмет не найден.")
            return
        await reply(message, 
            f"🛒 Выставить на торг\n{cat.format_item(it)}\n"
            f"{cat.format_buffs(it)}\n\n"
            f"Выбери цену или: торг {item_id} <цена>\n"
            f"({config.MARKET_MIN_PRICE}–{config.MARKET_MAX_PRICE}, "
            f"комиссия {int(config.MARKET_FEE*100)}%)",
            keyboard=market_price_keyboard(item_id).get_json(),
        )

    @bot.on.message(func=payload_cmd("mkt_list"))
    async def market_list_payload(message: Message):
        payload = message.get_payload_json() or {}
        item_id = str(payload.get("id") or "")
        price = int(payload.get("price") or 0)
        await _do_list(message, item_id, price)

    @bot.on.message(func=_is_list_text)
    async def market_list_text(message: Message):
        m = LIST_RE.match((message.text or "").strip())
        if not m:
            return
        item_id = m.group(1).strip()
        # allow name fuzzy: if not id, search catalog
        if not cat.get_item(item_id):
            found = cat.search_catalog(item_id, limit=1)
            if found:
                item_id = found[0]["id"]
        await _do_list(message, item_id, int(m.group(2)))


async def _browse(
    message: Message,
    *,
    query: str | None = None,
    page: int | None = None,
    rarity: str | None = None,
) -> None:
    payload = message.get_payload_json() or {}
    if page is None:
        page = int(payload.get("page") or 0)
    if rarity is None:
        rarity = payload.get("rarity") or None
    if query is None:
        query = payload.get("q") or None
    if rarity == "":
        rarity = None

    async with SessionLocal() as session:
        listings, has_next = await search_listings(
            session, rarity=rarity, query=query, page=page
        )
        title = "🛒 Витрина"
        if rarity:
            title += f" · {cat.RARITY_LABEL.get(rarity, rarity)}"
        if query:
            title += f" · «{query}»"
        if not listings:
            await reply(message, 
                f"{title}\nЛотов нет. Выстави из Сумки → На торг.",
                keyboard=market_menu_keyboard().get_json(),
            )
            return
        lines = [title, "Дешевле сверху. Жми лот — баффы и покупка.", ""]
        for listing in listings:
            it = cat.get_item(listing.item_id)
            short = (it.get("desc") or "")[:40] if it else ""
            lines.append(
                f"#{listing.id} {cat.format_item(it) if it else listing.item_id} "
                f"— {listing.price}💰"
            )
            if short:
                lines.append(f"   {short}")
        await reply(message, 
            "\n".join(lines),
            keyboard=market_listings_keyboard(
                listings,
                page=page,
                rarity=rarity,
                query=query,
                has_next=has_next,
            ).get_json(),
        )


async def _do_list(message: Message, item_id: str, price: int) -> None:
    name = await resolve_name(message)
    async with SessionLocal() as session:
        player = await get_or_create_player(session, message.from_id, name)
        try:
            listing = await create_listing(session, player, item_id, price)
        except MarketError as e:
            await reply(message, e.message, keyboard=market_menu_keyboard().get_json())
            return
        it = cat.get_item(item_id)
        await reply(message, 
            f"✅ Лот #{listing.id} выставлен за {price}💰\n"
            f"{cat.format_item(it) if it else item_id}\n"
            f"{cat.format_buffs(it) if it else ''}",
            keyboard=market_menu_keyboard().get_json(),
        )
