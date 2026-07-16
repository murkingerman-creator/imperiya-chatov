from vkbottle.bot import Bot, Message

from bot import config
from bot.keyboards import cancel_keyboard, main_keyboard, nation_keyboard
from db.database import SessionLocal
from handlers.common import resolve_name
from handlers.rules import match_cmd, payload_cmd, text_in
from services.nation import (
    NationError,
    count_citizens,
    found_nation,
    get_nation_by_chat,
    is_chat_peer,
    join_nation,
)
from services.player import get_or_create_player

# peer_id + user_id — чтобы в беседе не пересекались состояния игроков
_pending_found: set[tuple[int, int]] = set()

RESERVED = {
    "старт",
    "начать",
    "меню",
    "📋 меню",
    "профиль",
    "👤 профиль",
    "работа",
    "💼 работа",
    "страна",
    "🏛 страна",
    "моя страна",
    "война",
    "⚔ война",
    "рейд",
    "⚔ рейд",
    "топ",
    "топ стран",
    "🏆 топ стран",
    "топ игроков",
    "💰 топ игроков",
    "основать",
    "основать страну",
    "🏗 основать страну",
    "вступить",
    "➕ вступить",
    "отмена",
    "❌ отмена",
    "инфо страны",
    "ℹ️ инфо страны",
    "нужна беседа",
    "ℹ️ нужна беседа",
}


def register(bot: Bot) -> None:
    @bot.on.message(
        func=match_cmd("nation", "страна", "🏛 страна", "моя страна", "ℹ️ инфо страны", "инфо страны")
    )
    async def nation_menu(message: Message):
        name = await resolve_name(message)
        in_chat = is_chat_peer(message.peer_id)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            has_nation = bool(player.nation_id)
            is_leader = bool(
                player.nation and player.nation.leader_id == player.vk_id
            )

            if player.nation:
                citizens = await count_citizens(session, player.nation.id)
                text = (
                    f"🏛 {player.nation.flag_emoji} {player.nation.name}\n"
                    f"💰 Казна: {player.nation.treasury}\n"
                    f"👥 Граждан: {citizens}\n"
                    f"{'👑 Ты лидер' if is_leader else 'Статус: гражданин'}"
                )
            else:
                chat_nation = (
                    await get_nation_by_chat(session, message.peer_id) if in_chat else None
                )
                if chat_nation:
                    text = (
                        f"В этой беседе уже есть страна "
                        f"«{chat_nation.flag_emoji} {chat_nation.name}».\n"
                        f"Нажми «Вступить», чтобы стать гражданином."
                    )
                elif in_chat:
                    text = (
                        "В этой беседе ещё нет государства.\n"
                        f"Основание стоит {config.NATION_FOUND_COST} крон.\n"
                        "Нажми «Основать страну»."
                    )
                else:
                    text = (
                        "Страну можно основать только в беседе.\n"
                        "1) Создай беседу VK\n"
                        "2) Добавь сообщество «Империя чатов»\n"
                        "3) Напиши здесь «Страна» → «Основать»"
                    )

            await message.answer(
                text,
                keyboard=nation_keyboard(
                    in_chat=in_chat, has_nation=has_nation, is_leader=is_leader
                ).get_json(),
            )

    @bot.on.message(
        func=match_cmd("join_nation", "➕ вступить", "вступить")
    )
    async def join_handler(message: Message):
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            try:
                nation = await join_nation(session, player, message.peer_id)
            except NationError as e:
                await message.answer(e.message, keyboard=main_keyboard().get_json())
                return

            await message.answer(
                f"Добро пожаловать в {nation.flag_emoji} {nation.name}!\n"
                f"Теперь 10% с работы идёт в казну страны.",
                keyboard=main_keyboard().get_json(),
            )

    @bot.on.message(
        func=match_cmd("found_nation", "🏗 основать страну", "основать страну", "основать")
    )
    async def found_start(message: Message):
        if not is_chat_peer(message.peer_id):
            await message.answer(
                "Основать страну можно только в беседе.\n"
                "Добавь сообщество в чат и нажми «Основать» там.",
                keyboard=main_keyboard().get_json(),
            )
            return

        _pending_found.add((message.peer_id, message.from_id))
        await message.answer(
            f"Введи название страны (2–32 символа).\n"
            f"Стоимость: {config.NATION_FOUND_COST} крон.\n"
            f"Напиши «Отмена» чтобы выйти.",
            keyboard=cancel_keyboard().get_json(),
        )

    @bot.on.message(func=match_cmd("cancel", "❌ отмена", "отмена"))
    async def cancel_found(message: Message):
        key = (message.peer_id, message.from_id)
        if key in _pending_found:
            _pending_found.discard(key)
            await message.answer("Отменено.", keyboard=main_keyboard().get_json())
            return
        await message.answer("Ок.", keyboard=main_keyboard().get_json())

    @bot.on.message(func=match_cmd("need_chat", "ℹ️ нужна беседа", "нужна беседа"))
    async def need_chat(message: Message):
        await message.answer(
            "Добавь бота (сообщество) в беседу VK и пиши команды там.",
            keyboard=main_keyboard().get_json(),
        )

    @bot.on.message(blocking=False)
    async def found_finish(message: Message):
        key = (message.peer_id, message.from_id)
        if key not in _pending_found:
            return

        text = (message.text or "").strip()
        if not text:
            return

        if text.casefold() in {r.casefold() for r in RESERVED}:
            return
        if (message.get_payload_json() or {}).get("cmd"):
            return

        _pending_found.discard(key)
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            try:
                nation = await found_nation(session, player, message.peer_id, text)
            except NationError as e:
                _pending_found.add(key)
                await message.answer(e.message, keyboard=cancel_keyboard().get_json())
                return

            await message.answer(
                f"🎉 Основана страна {nation.flag_emoji} {nation.name}!\n"
                f"Ты лидер. Зови граждан кнопкой «Вступить».\n"
                f"💰 Казна: {nation.treasury}",
                keyboard=main_keyboard().get_json(),
            )
