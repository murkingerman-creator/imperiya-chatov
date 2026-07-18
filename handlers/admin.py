from vkbottle.bot import Bot, Message

from bot.config import is_admin
from bot.keyboards import admin_keyboard, cancel_keyboard
from db.database import SessionLocal
from handlers.common import reply, resolve_name, user_keyboard
from handlers.rules import match_cmd, payload_cmd
from services import admin as admin_svc
from services.admin import AdminError
from services.broadcast import broadcast, format_report
from services.chronicle import force_post_chronicle
from services.nation import NationError, dissolve_nation_by_name
from services.player import get_or_create_player
from services.suggestions import (
    SuggestionError,
    accept_suggestion,
    format_suggestions_list,
    list_pending,
    reject_suggestion,
)
import random

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
        await reply(message, err, keyboard=user_keyboard(message.from_id))
        return False
    return True


def register(bot: Bot) -> None:
    @bot.on.message(func=match_cmd("admin", "админ", "🛠 админ", "!admin"))
    async def admin_menu(message: Message):
        if not await _require(message):
            return
        await reply(message, 
            "🛠 Админка\n"
            "Текстовые команды:\n"
            "• !дать ID СУММА\n"
            "• !игрок ID\n"
            "• !кд ID\n"
            "• !энергия ID\n"
            "• !удалитьстрану Название\n"
            "• !объявление текст — во все беседы+ЛС\n"
            "• !объявление_беседы текст\n"
            "• !объявление_лс текст\n"
            "• !принять ID — принять предложение\n"
            "• !отклонить ID [причина]\n"
            "• !всем СУММА — кроны всем за обновление\n",
            keyboard=admin_keyboard().get_json(),
        )

    @bot.on.message(func=payload_cmd("adm_stats"))
    async def adm_stats(message: Message):
        if not await _require(message):
            return
        async with SessionLocal() as session:
            text = await admin_svc.stats(session)
            await reply(message, text, keyboard=admin_keyboard().get_json())

    @bot.on.message(func=payload_cmd("adm_nations"))
    async def adm_nations(message: Message):
        if not await _require(message):
            return
        async with SessionLocal() as session:
            text = await admin_svc.list_nations_short(session)
            await reply(message, text, keyboard=admin_keyboard().get_json())

    @bot.on.message(func=payload_cmd("adm_cd_self"))
    async def adm_cd_self(message: Message):
        if not await _require(message):
            return
        async with SessionLocal() as session:
            await get_or_create_player(session, message.from_id)
            p = await admin_svc.reset_cooldowns(session, message.from_id)
            await reply(message, 
                f"Кулдауны сброшены для {p.name}",
                keyboard=admin_keyboard().get_json(),
            )

    @bot.on.message(func=payload_cmd("adm_chronicle"))
    async def adm_chronicle(message: Message):
        if not await _require(message):
            return
        async with SessionLocal() as session:
            text = await force_post_chronicle(message.ctx_api, session)
            await reply(message, 
                "📜 Хроника отправлена на стену группы.\n\n" + text[:800],
                keyboard=admin_keyboard().get_json(),
            )

    @bot.on.message(func=payload_cmd("adm_bcast_chats"))
    async def adm_bcast_chats_ask(message: Message):
        if not await _require(message):
            return
        _pending[(message.peer_id, message.from_id)] = "bcast_chats"
        await reply(
            message,
            "📣 Рассылка во все беседы стран.\n"
            "Напиши текст объявления одним сообщением (или «отмена»).",
            keyboard=cancel_keyboard().get_json(),
        )

    @bot.on.message(func=payload_cmd("adm_bcast_dms"))
    async def adm_bcast_dms_ask(message: Message):
        if not await _require(message):
            return
        _pending[(message.peer_id, message.from_id)] = "bcast_dms"
        await reply(
            message,
            "✉️ Рассылка во все ЛС игроков.\n"
            "Напиши текст объявления одним сообщением (или «отмена»).\n"
            "Кто закрыл ЛС с ботом — не получит.",
            keyboard=cancel_keyboard().get_json(),
        )

    @bot.on.message(func=payload_cmd("adm_bcast_all"))
    async def adm_bcast_all_ask(message: Message):
        if not await _require(message):
            return
        _pending[(message.peer_id, message.from_id)] = "bcast_all"
        await reply(
            message,
            "📣✉️ Рассылка везде: беседы стран + ЛС.\n"
            "Напиши текст объявления одним сообщением (или «отмена»).",
            keyboard=cancel_keyboard().get_json(),
        )

    @bot.on.message(func=payload_cmd("adm_suggestions"))
    async def adm_suggestions(message: Message):
        if not await _require(message):
            return
        async with SessionLocal() as session:
            items = await list_pending(session)
            await reply(
                message,
                format_suggestions_list(items),
                keyboard=admin_keyboard().get_json(),
            )

    @bot.on.message(func=payload_cmd("adm_give_all"))
    async def adm_give_all_ask(message: Message):
        if not await _require(message):
            return
        _pending[(message.peer_id, message.from_id)] = "give_all"
        await reply(
            message,
            "🎁 Бонус всем за обновление\n"
            "Напиши сумму крон (число).\n"
            "Пример: 100\n"
            "Или «отмена».",
            keyboard=cancel_keyboard().get_json(),
        )

    @bot.on.message(func=payload_cmd("adm_give"))
    async def adm_give_ask(message: Message):
        if not await _require(message):
            return
        _pending[(message.peer_id, message.from_id)] = "give"
        await reply(message, 
            "Формат: ID СУММА\nПример: 525336510 1000",
            keyboard=cancel_keyboard().get_json(),
        )

    @bot.on.message(func=payload_cmd("adm_energy"))
    async def adm_energy_ask(message: Message):
        if not await _require(message):
            return
        _pending[(message.peer_id, message.from_id)] = "energy"
        await reply(message, 
            "VK ID игрока для полной энергии:",
            keyboard=cancel_keyboard().get_json(),
        )

    @bot.on.message(func=payload_cmd("adm_cd"))
    async def adm_cd_ask(message: Message):
        if not await _require(message):
            return
        _pending[(message.peer_id, message.from_id)] = "cd"
        await reply(message, 
            "VK ID игрока для сброса кулдаунов:",
            keyboard=cancel_keyboard().get_json(),
        )

    @bot.on.message(func=payload_cmd("adm_player"))
    async def adm_player_ask(message: Message):
        if not await _require(message):
            return
        _pending[(message.peer_id, message.from_id)] = "player"
        await reply(message, 
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
        await reply(message, 
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
        if lower.startswith("!объявление ") or lower.startswith("!broadcast "):
            body = text.split(maxsplit=1)[1].strip()
            await _do_broadcast(message, body, to_chats=True, to_dms=True)
            return
        if lower.startswith("!объявление_беседы "):
            body = text.split(maxsplit=1)[1].strip()
            await _do_broadcast(message, body, to_chats=True, to_dms=False)
            return
        if lower.startswith("!объявление_лс "):
            body = text.split(maxsplit=1)[1].strip()
            await _do_broadcast(message, body, to_chats=False, to_dms=True)
            return
        if lower.startswith("!принять ") or lower.startswith("!accept "):
            parts = text.split(maxsplit=1)
            if len(parts) >= 2 and parts[1].strip().split()[0].isdigit():
                await _do_accept(message, int(parts[1].strip().split()[0]))
            else:
                await reply(
                    message,
                    "Формат: !принять ID",
                    keyboard=admin_keyboard().get_json(),
                )
            return
        if lower.startswith("!отклонить ") or lower.startswith("!reject "):
            parts = text.split(maxsplit=2)
            if len(parts) >= 2 and parts[1].isdigit():
                note = parts[2] if len(parts) >= 3 else ""
                await _do_reject(message, int(parts[1]), note)
            else:
                await reply(
                    message,
                    "Формат: !отклонить ID [причина]",
                    keyboard=admin_keyboard().get_json(),
                )
            return
        if lower.startswith("!всем ") or lower.startswith("!giveall "):
            parts = text.split()
            if len(parts) >= 2:
                try:
                    amount = int(parts[1])
                except ValueError:
                    amount = None
                if amount is not None:
                    await _do_give_all(message, amount)
                else:
                    await reply(
                        message,
                        "Формат: !всем СУММА",
                        keyboard=admin_keyboard().get_json(),
                    )
            else:
                await reply(
                    message,
                    "Формат: !всем СУММА",
                    keyboard=admin_keyboard().get_json(),
                )
            return

        key = (message.peer_id, message.from_id)
        mode = _pending.get(key)
        if not mode:
            return
        if lower in {"отмена", "❌ отмена", "cancel"}:
            _pending.pop(key, None)
            await reply(message, "Отменено.", keyboard=admin_keyboard().get_json())
            return

        if mode in {"bcast_chats", "bcast_dms", "bcast_all"}:
            _pending.pop(key, None)
            await _do_broadcast(
                message,
                text,
                to_chats=mode in {"bcast_chats", "bcast_all"},
                to_dms=mode in {"bcast_dms", "bcast_all"},
            )
            return

        _pending.pop(key, None)
        try:
            if mode == "give":
                parts = text.split()
                await _do_give(message, int(parts[0]), int(parts[1]))
            elif mode == "give_all":
                await _do_give_all(message, int(text.split()[0]))
            elif mode == "energy":
                await _do_energy(message, int(text.split()[0]))
            elif mode == "cd":
                await _do_cd(message, int(text.split()[0]))
            elif mode == "player":
                await _do_player(message, int(text.split()[0]))
            elif mode == "del_nation":
                await _do_del_nation(message, text)
        except (ValueError, IndexError):
            await reply(message, "Неверный формат.", keyboard=admin_keyboard().get_json())


async def _do_broadcast(
    message: Message,
    text: str,
    *,
    to_chats: bool,
    to_dms: bool,
) -> None:
    if not await _require(message):
        return
    await reply(
        message,
        "⏳ Рассылка идёт… это может занять минуту.",
        keyboard=admin_keyboard().get_json(),
    )
    async with SessionLocal() as session:
        try:
            result = await broadcast(
                message.ctx_api,
                session,
                text,
                to_chats=to_chats,
                to_dms=to_dms,
            )
        except ValueError as e:
            await reply(message, str(e), keyboard=admin_keyboard().get_json())
            return
    await reply(message, format_report(result), keyboard=admin_keyboard().get_json())


async def _do_give(message: Message, vk_id: int, amount: int) -> None:
    async with SessionLocal() as session:
        try:
            p = await admin_svc.give_crowns(session, vk_id, amount)
        except AdminError as e:
            await reply(message, e.message, keyboard=admin_keyboard().get_json())
            return
        await reply(message, 
            f"✅ {p.name} ({vk_id}): {amount:+d} крон → {p.crowns}",
            keyboard=admin_keyboard().get_json(),
        )


async def _do_give_all(message: Message, amount: int) -> None:
    if not await _require(message):
        return
    async with SessionLocal() as session:
        try:
            result = await admin_svc.give_crowns_all(session, amount)
        except AdminError as e:
            await reply(message, e.message, keyboard=admin_keyboard().get_json())
            return
    await reply(
        message,
        f"🎁 Всем начислено {amount:+d} крон\n"
        f"Игроков: {result['count']}\n"
        f"Всего выдано: {result['total']:+d}",
        keyboard=admin_keyboard().get_json(),
    )


async def _do_energy(message: Message, vk_id: int) -> None:
    async with SessionLocal() as session:
        try:
            p = await admin_svc.fill_energy(session, vk_id)
        except AdminError as e:
            await reply(message, e.message, keyboard=admin_keyboard().get_json())
            return
        await reply(message, 
            f"⚡ {p.name}: энергия полная ({p.energy})",
            keyboard=admin_keyboard().get_json(),
        )


async def _do_cd(message: Message, vk_id: int) -> None:
    async with SessionLocal() as session:
        try:
            p = await admin_svc.reset_cooldowns(session, vk_id)
        except AdminError as e:
            await reply(message, e.message, keyboard=admin_keyboard().get_json())
            return
        await reply(message, 
            f"⏱ Кулдауны сброшены: {p.name}",
            keyboard=admin_keyboard().get_json(),
        )


async def _do_player(message: Message, vk_id: int) -> None:
    async with SessionLocal() as session:
        try:
            text = await admin_svc.get_player_info(session, vk_id)
        except AdminError as e:
            await reply(message, e.message, keyboard=admin_keyboard().get_json())
            return
        await reply(message, text, keyboard=admin_keyboard().get_json())


async def _do_del_nation(message: Message, name: str) -> None:
    async with SessionLocal() as session:
        try:
            deleted = await dissolve_nation_by_name(session, name)
        except NationError as e:
            await reply(message, e.message, keyboard=admin_keyboard().get_json())
            return
        await reply(message, 
            f"🗑 Удалена страна {deleted}",
            keyboard=admin_keyboard().get_json(),
        )


async def _notify_author(message: Message, user_id: int, text: str) -> bool:
    try:
        await message.ctx_api.messages.send(
            user_id=user_id,
            message=text,
            random_id=random.randint(1, 2_000_000_000),
        )
        return True
    except Exception:
        return False


async def _do_accept(message: Message, sug_id: int) -> None:
    if not await _require(message):
        return
    async with SessionLocal() as session:
        try:
            result = await accept_suggestion(session, sug_id)
        except SuggestionError as e:
            await reply(message, e.message, keyboard=admin_keyboard().get_json())
            return
        sug = result["suggestion"]
        reward = result["reward"]
        author_id = sug.author_vk_id
        author_name = sug.author_name
        body = sug.text
        crowns = result["crowns"]

    dm = (
        f"✅ Твоё предложение #{sug_id} принято!\n\n"
        f"«{body}»\n\n"
        f"Награда: +{reward} крон"
        + (f" (баланс {crowns})." if crowns is not None else ".")
        + "\nСпасибо — идея пойдёт в работу."
    )
    dm_ok = await _notify_author(message, author_id, dm)
    await reply(
        message,
        f"✅ #{sug_id} принято · {author_name}\n"
        f"+{reward} крон автору"
        + (" · ЛС отправлено" if dm_ok else " · ЛС не доставлено (закрыты)"),
        keyboard=admin_keyboard().get_json(),
    )


async def _do_reject(message: Message, sug_id: int, note: str = "") -> None:
    if not await _require(message):
        return
    async with SessionLocal() as session:
        try:
            result = await reject_suggestion(session, sug_id, note)
        except SuggestionError as e:
            await reply(message, e.message, keyboard=admin_keyboard().get_json())
            return
        sug = result["suggestion"]
        author_id = sug.author_vk_id
        author_name = sug.author_name
        body = sug.text
        reason = (note or "").strip()

    dm = f"❌ Твоё предложение #{sug_id} отклонено.\n\n«{body}»"
    if reason:
        dm += f"\n\nПричина: {reason}"
    dm_ok = await _notify_author(message, author_id, dm)
    await reply(
        message,
        f"❌ #{sug_id} отклонено · {author_name}"
        + (f"\nПричина: {reason}" if reason else "")
        + (" · ЛС отправлено" if dm_ok else " · ЛС не доставлено"),
        keyboard=admin_keyboard().get_json(),
    )
