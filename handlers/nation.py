from vkbottle.bot import Bot, Message

from bot import config
from bot.keyboards import (
    confirm_dissolve_keyboard,
    citizens_keyboard,
    customize_keyboard,
    main_keyboard,
    nation_keyboard,
    preset_keyboard,
    tax_keyboard,
    cancel_keyboard,
)
from db.database import SessionLocal
from handlers.common import reply, resolve_chat_peer, resolve_name, remember_chat_peer
from handlers.rules import match_cmd, payload_cmd
from services.chronicle_store import add_event
from services.customize import CustomizeError, set_field
from services.onboarding import advance_onboarding
from services.nation import (
    NationError,
    count_citizens,
    dissolve_nation,
    format_nation_card,
    found_nation,
    get_nation_by_chat,
    join_nation,
    leave_nation,
    list_citizens,
    transfer_leadership,
)
from services.notify import notify_nation_chat
from services.player import get_or_create_player

# vk_id -> chat_peer_id (ожидание названия страны)
_pending_found: dict[int, int] = {}
# vk_id -> field name (ожидание текста оформления)
_pending_text: dict[int, str] = {}

RESERVED = {
    "старт", "начать", "меню", "📋 меню", "профиль", "👤 профиль",
    "работа", "💼 работа", "работы", "страна", "🏛 страна", "моя страна",
    "война", "⚔ война", "рейд", "топ", "топ стран", "🏆 топ стран",
    "топ игроков", "💰 топ игроков", "основать", "основать страну",
    "🏗 основать страну", "вступить", "➕ вступить", "отмена", "❌ отмена",
    "ежедневка", "🎁 ежедневка", "инвайт", "📨 инвайт", "выйти", "🚪 выйти",
}


def register(bot: Bot) -> None:
    @bot.on.message(
        func=match_cmd(
            "nation", "страна", "🏛 страна", "моя страна", "ℹ️ инфо страны", "инфо страны"
        )
    )
    async def nation_menu(message: Message):
        remember_chat_peer(message)
        name = await resolve_name(message)
        chat_peer = resolve_chat_peer(message)
        in_chat = chat_peer is not None
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            has_nation = bool(player.nation_id)
            is_leader = bool(player.nation and player.nation.leader_id == player.vk_id)

            if player.nation:
                citizens = await count_citizens(session, player.nation.id)
                text = format_nation_card(player.nation, citizens)
                if is_leader:
                    text += "\n👑 Ты лидер"
            else:
                chat_nation = (
                    await get_nation_by_chat(session, chat_peer) if chat_peer else None
                )
                if chat_nation:
                    text = (
                        f"В беседе: {chat_nation.flag_emoji} {chat_nation.name}\n"
                        "Нажми «Вступить»."
                    )
                elif in_chat:
                    text = (
                        f"Страны ещё нет. Основание: {config.NATION_FOUND_COST} крон.\n"
                        "Нажми «Основать страну»."
                    )
                else:
                    text = (
                        "Страну основывают только в беседе.\n"
                        "Добавь сообщество в чат → Страна → Основать."
                    )

            await reply(message, 
                text,
                keyboard=nation_keyboard(
                    in_chat=in_chat, has_nation=has_nation, is_leader=is_leader
                ).get_json(),
            )

    @bot.on.message(func=match_cmd("join_nation", "➕ вступить", "вступить"))
    async def join_handler(message: Message):
        remember_chat_peer(message)
        name = await resolve_name(message)
        chat_peer = resolve_chat_peer(message)
        if not chat_peer:
            await reply(
                message,
                "Вступить можно из беседы (или сначала открой «Страна» в беседе).",
                keyboard=main_keyboard().get_json(),
            )
            return
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            try:
                nation = await join_nation(session, player, chat_peer)
            except NationError as e:
                await reply(message, e.message, keyboard=main_keyboard().get_json())
                return
            welcome = nation.welcome or "Добро пожаловать!"
            await notify_nation_chat(
                message.ctx_api,
                nation.chat_peer_id,
                f"➕ {player.name} вступил в {nation.flag_emoji} {nation.name}!",
            )
            await reply(message, 
                f"{welcome}\nТы в {nation.flag_emoji} {nation.name}.\n"
                f"Налог страны: {int((nation.tax_rate or 0.1)*100)}%"
                + (f"\n{ob}" if (ob := await advance_onboarding(session, player, "nation")) else ""),
                keyboard=main_keyboard().get_json(),
            )

    @bot.on.message(
        func=match_cmd("found_nation", "🏗 основать страну", "основать страну", "основать")
    )
    async def found_start(message: Message):
        remember_chat_peer(message)
        chat_peer = resolve_chat_peer(message)
        if not chat_peer:
            await reply(message, 
                "Основать страну можно только из беседы.\n"
                "Напиши «Страна» в беседе, затем «Основать» в ЛС.",
                keyboard=main_keyboard().get_json(),
            )
            return
        _pending_found[message.from_id] = chat_peer
        await reply(message, 
            f"Название страны (2–32 символа).\nЦена: {config.NATION_FOUND_COST} крон.\n"
            f"Ответь сюда (в ЛС) названием.",
            keyboard=cancel_keyboard().get_json(),
        )

    @bot.on.message(func=match_cmd("leave_nation", "🚪 выйти", "выйти"))
    async def leave_handler(message: Message):
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            try:
                msg = await leave_nation(session, player)
            except NationError as e:
                await reply(message, e.message, keyboard=main_keyboard().get_json())
                return
            await reply(message, msg, keyboard=main_keyboard().get_json())

    @bot.on.message(func=match_cmd("dissolve_nation", "🗑 распустить", "распустить"))
    async def dissolve_ask(message: Message):
        await reply(message, 
            "⚠ Распустить страну навсегда?\nВсе граждане станут без страны (кулдаун 24ч).",
            keyboard=confirm_dissolve_keyboard().get_json(),
        )

    @bot.on.message(func=payload_cmd("dissolve_confirm"))
    async def dissolve_do(message: Message):
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            try:
                nation_name = await dissolve_nation(session, player)
            except NationError as e:
                await reply(message, e.message, keyboard=main_keyboard().get_json())
                return
            await add_event(session, "dissolve", f"Страна {nation_name} распущена")
            await reply(message, 
                f"🗑 Страна {nation_name} удалена. Беседу можно основать заново.",
                keyboard=main_keyboard().get_json(),
            )

    @bot.on.message(func=match_cmd("transfer_menu", "👑 трон", "трон", "передать трон"))
    async def transfer_menu(message: Message):
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            if not player.nation or player.nation.leader_id != player.vk_id:
                await reply(message, "Только лидер.", keyboard=main_keyboard().get_json())
                return
            citizens = [
                c
                for c in await list_citizens(session, player.nation.id, 8)
                if c.vk_id != player.vk_id
            ]
            if not citizens:
                await reply(message, 
                    "Некому передавать трон (ты один).",
                    keyboard=main_keyboard().get_json(),
                )
                return
            await reply(message, 
                "Выбери нового лидера:",
                keyboard=citizens_keyboard(citizens).get_json(),
            )

    @bot.on.message(func=payload_cmd("transfer_to"))
    async def transfer_do(message: Message):
        payload = message.get_payload_json() or {}
        target_id = int(payload.get("vk_id") or 0)
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            try:
                target = await transfer_leadership(session, player, target_id)
            except NationError as e:
                await reply(message, e.message, keyboard=main_keyboard().get_json())
                return
            await notify_nation_chat(
                message.ctx_api,
                player.nation.chat_peer_id if player.nation else message.peer_id,
                f"👑 Новый лидер: {target.name}!",
            )
            await reply(message, 
                f"Трон передан: {target.name}",
                keyboard=main_keyboard().get_json(),
            )

    @bot.on.message(func=match_cmd("cancel", "❌ отмена", "отмена"))
    async def cancel_found(message: Message):
        _pending_found.pop(message.from_id, None)
        _pending_text.pop(message.from_id, None)
        await reply(message, "Отменено.", keyboard=main_keyboard().get_json())

    @bot.on.message(func=match_cmd("need_chat", "ℹ️ нужна беседа", "нужна беседа"))
    async def need_chat(message: Message):
        await reply(message, 
            "Добавь сообщество в беседу VK.",
            keyboard=main_keyboard().get_json(),
        )

    @bot.on.message(blocking=False)
    async def found_finish(message: Message):
        text = (message.text or "").strip()
        if not text:
            return

        # customize text input
        if message.from_id in _pending_text:
            field = _pending_text.pop(message.from_id)
            name = await resolve_name(message)
            async with SessionLocal() as session:
                player = await get_or_create_player(session, message.from_id, name)
                try:
                    result = await set_field(session, player, field, text)
                except CustomizeError as e:
                    _pending_text[message.from_id] = field
                    await reply(message, e.message, keyboard=cancel_keyboard().get_json())
                    return
                cost_line = f"\n−{result['cost']} крон" if result["cost"] else ""
                await reply(message, 
                    f"Сохранено ({field}){cost_line}",
                    keyboard=customize_keyboard().get_json(),
                )
            return

        if message.from_id not in _pending_found:
            return
        if text.casefold() in {r.casefold() for r in RESERVED}:
            return
        if (message.get_payload_json() or {}).get("cmd"):
            return

        chat_peer = _pending_found.pop(message.from_id)
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            try:
                nation = await found_nation(session, player, chat_peer, text)
            except NationError as e:
                _pending_found[message.from_id] = chat_peer
                await reply(message, e.message, keyboard=cancel_keyboard().get_json())
                return

            await add_event(
                session,
                "found",
                f"{nation.flag_emoji} {nation.name} (лидер {player.name})",
                str(nation.id),
            )
            await notify_nation_chat(
                message.ctx_api,
                nation.chat_peer_id,
                f"🎉 Основана страна {nation.flag_emoji} {nation.name}!\nЛидер: {player.name}",
            )
            from services.chronicle import post_flash

            await post_flash(
                message.ctx_api,
                session,
                f"🏛 Основана {nation.flag_emoji} {nation.name}! Лидер: {player.name}",
            )
            onboard = await advance_onboarding(session, player, "nation")
            onboard_line = f"\n{onboard}" if onboard else ""
            await reply(message, 
                f"🎉 Основана {nation.flag_emoji} {nation.name}!\n"
                f"Оформи: 🎨 · Зови друзей: 📨{onboard_line}",
                keyboard=main_keyboard().get_json(),
            )


# shared pending for customize module
def get_pending_text() -> dict:
    return _pending_text
