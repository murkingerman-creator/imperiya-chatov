from vkbottle.bot import Bot, Message

from bot.config import is_admin
from bot.keyboards import admin_keyboard, cancel_keyboard
from db.database import SessionLocal
from handlers.common import resolve_name, user_keyboard
from handlers.rules import match_cmd, payload_cmd
from services import admin as admin_svc
from services.admin import AdminError
from services.chronicle import force_post_chronicle
from services.nation import NationError, dissolve_nation_by_name
from services.player import get_or_create_player

# peer_id + from_id -> mode
_pending: dict[tuple[int, int], str] = {}


def _dm_only(message: Message) -> bool:
    return message.peer_id == message.from_id


def _guard(message: Message) -> str | None:
    if not is_admin(message.from_id):
        return "Нет доступа."
    if not _dm_only(message):
        return "Админка только в ЛС боту."
    return None


async def _require(message: Message) -> bool:
    err = _guard(message)
    if err:
        await message.answer(err, keyboard=user_keyboard(message.from_id))
        return False
    return True


def register(bot: Bot) -> None:
    @bot.on.message(func=match_cmd("admin", "админ", "🛠 админ", "!admin"))
    async def admin_menu(message: Message):
        if not await _require(message):
            return
        await message.answer(
            "🛠 Админка\n"
            "Текстовые команды:\n"
            "• !дать ID СУММА\n"
            "• !игрок ID\n"
            "• !кд ID\n"
            "• !энергия ID\n"
            "• !удалитьстрану Название\n",
            keyboard=admin_keyboard().get_json(),
        )

    @bot.on.message(func=payload_cmd("adm_stats"))
    async def adm_stats(message: Message):
        if not await _require(message):
            return
        async with SessionLocal() as session:
            text = await admin_svc.stats(session)
            await message.answer(text, keyboard=admin_keyboard().get_json())

    @bot.on.message(func=payload_cmd("adm_nations"))
    async def adm_nations(message: Message):
        if not await _require(message):
            return
        async with SessionLocal() as session:
            text = await admin_svc.list_nations_short(session)
            await message.answer(text, keyboard=admin_keyboard().get_json())

    @bot.on.message(func=payload_cmd("adm_cd_self"))
    async def adm_cd_self(message: Message):
        if not await _require(message):
            return
        async with SessionLocal() as session:
            await get_or_create_player(session, message.from_id)
            p = await admin_svc.reset_cooldowns(session, message.from_id)
            await message.answer(
                f"Кулдауны сброшены для {p.name}",
                keyboard=admin_keyboard().get_json(),
            )

    @bot.on.message(func=payload_cmd("adm_chronicle"))
    async def adm_chronicle(message: Message):
        if not await _require(message):
            return
        async with SessionLocal() as session:
            text = await force_post_chronicle(message.ctx_api, session)
            await message.answer(
                "📜 Хроника отправлена на стену группы.\n\n" + text[:800],
                keyboard=admin_keyboard().get_json(),
            )

    @bot.on.message(func=payload_cmd("adm_give"))
    async def adm_give_ask(message: Message):
        if not await _require(message):
            return
        _pending[(message.peer_id, message.from_id)] = "give"
        await message.answer(
            "Формат: ID СУММА\nПример: 525336510 1000",
            keyboard=cancel_keyboard().get_json(),
        )

    @bot.on.message(func=payload_cmd("adm_energy"))
    async def adm_energy_ask(message: Message):
        if not await _require(message):
            return
        _pending[(message.peer_id, message.from_id)] = "energy"
        await message.answer(
            "VK ID игрока для полной энергии:",
            keyboard=cancel_keyboard().get_json(),
        )

    @bot.on.message(func=payload_cmd("adm_cd"))
    async def adm_cd_ask(message: Message):
        if not await _require(message):
            return
        _pending[(message.peer_id, message.from_id)] = "cd"
        await message.answer(
            "VK ID игрока для сброса кулдаунов:",
            keyboard=cancel_keyboard().get_json(),
        )

    @bot.on.message(func=payload_cmd("adm_player"))
    async def adm_player_ask(message: Message):
        if not await _require(message):
            return
        _pending[(message.peer_id, message.from_id)] = "player"
        await message.answer(
            "VK ID игрока:",
            keyboard=cancel_keyboard().get_json(),
        )

    @bot.on.message(func=payload_cmd("adm_del_nation"))
    async def adm_del_ask(message: Message):
        if not await _require(message):
            return
        _pending[(message.peer_id, message.from_id)] = "del_nation"
        async with SessionLocal() as session:
            listing = await admin_svc.list_nations_short(session)
        await message.answer(
            f"{listing}\n\n"
            "Напиши название или id страны для удаления.\n"
            "Примеры: Тест  |  1  |  id=1",
            keyboard=cancel_keyboard().get_json(),
        )

    @bot.on.message(blocking=False)
    async def admin_text_flow(message: Message):
        if not is_admin(message.from_id) or not _dm_only(message):
            return

        text = (message.text or "").strip()
        if not text:
            return

        # slash-like commands
        lower = text.casefold()
        if lower.startswith("!дать ") or lower.startswith("!give "):
            parts = text.split()
            if len(parts) >= 3 and parts[1].isdigit():
                await _do_give(message, int(parts[1]), int(parts[2]))
            else:
                await message.answer("Формат: !дать ID СУММА")
            return
        if lower.startswith("!игрок ") or lower.startswith("!player "):
            parts = text.split()
            if len(parts) >= 2 and parts[1].isdigit():
                await _do_player(message, int(parts[1]))
            return
        if lower.startswith("!кд ") or lower.startswith("!cd "):
            parts = text.split()
            if len(parts) >= 2 and parts[1].isdigit():
                await _do_cd(message, int(parts[1]))
            return
        if lower.startswith("!энергия ") or lower.startswith("!energy "):
            parts = text.split()
            if len(parts) >= 2 and parts[1].isdigit():
                await _do_energy(message, int(parts[1]))
            return
        if lower.startswith("!удалитьстрану ") or lower.startswith("!delnation "):
            name = text.split(maxsplit=1)[1].strip()
            await _do_del_nation(message, name)
            return

        key = (message.peer_id, message.from_id)
        mode = _pending.get(key)
        if not mode:
            return
        if lower in {"отмена", "❌ отмена", "cancel"}:
            _pending.pop(key, None)
            await message.answer("Отменено.", keyboard=admin_keyboard().get_json())
            return

        _pending.pop(key, None)
        try:
            if mode == "give":
                parts = text.split()
                await _do_give(message, int(parts[0]), int(parts[1]))
            elif mode == "energy":
                await _do_energy(message, int(text.split()[0]))
            elif mode == "cd":
                await _do_cd(message, int(text.split()[0]))
            elif mode == "player":
                await _do_player(message, int(text.split()[0]))
            elif mode == "del_nation":
                await _do_del_nation(message, text)
        except (ValueError, IndexError):
            await message.answer("Неверный формат.", keyboard=admin_keyboard().get_json())


async def _do_give(message: Message, vk_id: int, amount: int) -> None:
    async with SessionLocal() as session:
        try:
            p = await admin_svc.give_crowns(session, vk_id, amount)
        except AdminError as e:
            await message.answer(e.message, keyboard=admin_keyboard().get_json())
            return
        await message.answer(
            f"✅ {p.name} ({vk_id}): {amount:+d} крон → {p.crowns}",
            keyboard=admin_keyboard().get_json(),
        )


async def _do_energy(message: Message, vk_id: int) -> None:
    async with SessionLocal() as session:
        try:
            p = await admin_svc.fill_energy(session, vk_id)
        except AdminError as e:
            await message.answer(e.message, keyboard=admin_keyboard().get_json())
            return
        await message.answer(
            f"⚡ {p.name}: энергия полная ({p.energy})",
            keyboard=admin_keyboard().get_json(),
        )


async def _do_cd(message: Message, vk_id: int) -> None:
    async with SessionLocal() as session:
        try:
            p = await admin_svc.reset_cooldowns(session, vk_id)
        except AdminError as e:
            await message.answer(e.message, keyboard=admin_keyboard().get_json())
            return
        await message.answer(
            f"⏱ Кулдауны сброшены: {p.name}",
            keyboard=admin_keyboard().get_json(),
        )


async def _do_player(message: Message, vk_id: int) -> None:
    async with SessionLocal() as session:
        try:
            text = await admin_svc.get_player_info(session, vk_id)
        except AdminError as e:
            await message.answer(e.message, keyboard=admin_keyboard().get_json())
            return
        await message.answer(text, keyboard=admin_keyboard().get_json())


async def _do_del_nation(message: Message, name: str) -> None:
    async with SessionLocal() as session:
        try:
            deleted = await dissolve_nation_by_name(session, name)
        except NationError as e:
            await message.answer(e.message, keyboard=admin_keyboard().get_json())
            return
        await message.answer(
            f"🗑 Удалена страна {deleted}",
            keyboard=admin_keyboard().get_json(),
        )
