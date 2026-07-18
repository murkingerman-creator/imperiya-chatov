import random

from vkbottle.bot import Bot, Message

from bot import config
from bot.config import is_admin
from bot.keyboards import (
    admin_events_keyboard,
    admin_extra_keyboard,
    admin_keyboard,
    cancel_keyboard,
)
from db.database import SessionLocal
from handlers.common import reply, user_keyboard
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
from services.bugs import (
    BugError,
    accept_bug,
    format_bugs_list,
    list_pending_bugs,
    reject_bug,
)
from services.flash_events import (
    clear_flash,
    force_flash,
    format_flash_announce,
    format_flash_event,
    get_flash_event,
    list_flashes_text,
)
from services.world_events import clear_event, force_event, format_event, get_active_event

# peer_id + from_id -> mode
_pending: dict[tuple[int, int], str] = {}
# for event start: (peer, from) -> event key waiting hours
_pending_event: dict[tuple[int, int], str] = {}


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


def _help_text() -> str:
    return (
        "🛠 Админка\n"
        "• !дать / !тюрьма / !свобода / !предмет / !титул\n"
        "• !ивент KEY [часы] · !стоп_ивент\n"
        "• !вспышка [KEY] [часы] · !вспышка_стоп\n"
        "• !джекпот СУММА · !дождь Название СУММА\n"
        "• !всем СУММА [текст] · !принять / !отклонить\n"
        "• !багпринять ID · !баготклонить ID [причина]\n"
        "🌤 Ивенты · 🎮 Ещё — расширенные действия"
    )


def register(bot: Bot) -> None:
    @bot.on.message(func=match_cmd("admin", "админ", "🛠 админ", "!admin"))
    async def admin_menu(message: Message):
        if not await _require(message):
            return
        await reply(message, _help_text(), keyboard=admin_keyboard().get_json())

    @bot.on.message(func=payload_cmd("adm_extra"))
    async def adm_extra(message: Message):
        if not await _require(message):
            return
        await reply(
            message,
            "🎮 Доп. админка: модерация, подарки, ивент-фан.",
            keyboard=admin_extra_keyboard().get_json(),
        )

    @bot.on.message(func=payload_cmd("adm_events"))
    async def adm_events(message: Message):
        if not await _require(message):
            return
        async with SessionLocal() as session:
            ev = await get_active_event(session)
            flash = await get_flash_event(session)
        await reply(
            message,
            f"🌤 Мировые ивенты\n"
            f"Сутки: {format_event(ev)}\n"
            f"{format_flash_event(flash)}\n\n"
            f"Дневной: кнопка → часы "
            f"(пусто = {config.ADMIN_EVENT_DEFAULT_HOURS}ч).\n"
            f"⚡ Вспышка ★ — случайная из 30 (авто раз в 2–3ч).\n"
            f"!вспышка KEY [часы] · !вспышка_стоп",
            keyboard=admin_events_keyboard().get_json(),
        )

    @bot.on.message(func=payload_cmd("adm_ev_status"))
    async def adm_ev_status(message: Message):
        if not await _require(message):
            return
        async with SessionLocal() as session:
            ev = await get_active_event(session)
            flash = await get_flash_event(session)
        await reply(
            message,
            f"{format_event(ev)}\n\n{format_flash_event(flash)}",
            keyboard=admin_events_keyboard().get_json(),
        )

    @bot.on.message(func=payload_cmd("adm_ev_stop"))
    async def adm_ev_stop(message: Message):
        if not await _require(message):
            return
        await _do_stop_event(message)

    @bot.on.message(func=payload_cmd("adm_flash_rand"))
    async def adm_flash_rand(message: Message):
        if not await _require(message):
            return
        await _do_force_flash(message, key=None, hours=None)

    @bot.on.message(func=payload_cmd("adm_flash_list"))
    async def adm_flash_list(message: Message):
        if not await _require(message):
            return
        text = list_flashes_text()
        # VK message limit ~4000
        if len(text) > 3800:
            mid = len(text) // 2
            split = text.rfind("\n• ", 0, mid)
            if split < 0:
                split = mid
            await reply(
                message,
                text[:split].strip(),
                keyboard=admin_events_keyboard().get_json(),
            )
            await reply(
                message,
                text[split:].strip(),
                keyboard=admin_events_keyboard().get_json(),
            )
        else:
            await reply(
                message, text, keyboard=admin_events_keyboard().get_json()
            )

    @bot.on.message(func=payload_cmd("adm_flash_stop"))
    async def adm_flash_stop(message: Message):
        if not await _require(message):
            return
        await _do_stop_flash(message)

    @bot.on.message(func=payload_cmd("adm_ev"))
    async def adm_ev_ask(message: Message):
        if not await _require(message):
            return
        payload = message.get_payload_json() or {}
        key = str(payload.get("key") or "")
        if key not in config.WORLD_EVENTS:
            await reply(
                message,
                "Неизвестный ивент.",
                keyboard=admin_events_keyboard().get_json(),
            )
            return
        info = config.WORLD_EVENTS[key]
        _pending[(message.peer_id, message.from_id)] = "event_hours"
        _pending_event[(message.peer_id, message.from_id)] = key
        await reply(
            message,
            f"{info['title']}\n{info['desc']}\n\n"
            f"Сколько часов? (пусто/{config.ADMIN_EVENT_DEFAULT_HOURS} = по умолчанию)\n"
            f"Или «отмена».",
            keyboard=cancel_keyboard().get_json(),
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
            await reply(
                message,
                f"Кулдауны сброшены для {p.name}",
                keyboard=admin_extra_keyboard().get_json(),
            )

    @bot.on.message(func=payload_cmd("adm_chronicle"))
    async def adm_chronicle(message: Message):
        if not await _require(message):
            return
        async with SessionLocal() as session:
            text = await force_post_chronicle(message.ctx_api, session)
            await reply(
                message,
                "📜 Хроника отправлена на стену группы.\n\n" + text[:800],
                keyboard=admin_extra_keyboard().get_json(),
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

    @bot.on.message(func=payload_cmd("adm_bugs"))
    async def adm_bugs(message: Message):
        if not await _require(message):
            return
        async with SessionLocal() as session:
            items = await list_pending_bugs(session)
            await reply(
                message,
                format_bugs_list(items),
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
            "Формат: СУММА или СУММА текст\n"
            "Пример: 100\nИли «отмена».",
            keyboard=cancel_keyboard().get_json(),
        )

    @bot.on.message(func=payload_cmd("adm_give"))
    async def adm_give_ask(message: Message):
        if not await _require(message):
            return
        _pending[(message.peer_id, message.from_id)] = "give"
        await reply(
            message,
            "Формат: ID СУММА\nПример: 525336510 1000",
            keyboard=cancel_keyboard().get_json(),
        )

    @bot.on.message(func=payload_cmd("adm_energy"))
    async def adm_energy_ask(message: Message):
        if not await _require(message):
            return
        _pending[(message.peer_id, message.from_id)] = "energy"
        await reply(
            message,
            "VK ID игрока для полной энергии:",
            keyboard=cancel_keyboard().get_json(),
        )

    @bot.on.message(func=payload_cmd("adm_cd"))
    async def adm_cd_ask(message: Message):
        if not await _require(message):
            return
        _pending[(message.peer_id, message.from_id)] = "cd"
        await reply(
            message,
            "VK ID игрока для сброса кулдаунов:",
            keyboard=cancel_keyboard().get_json(),
        )

    @bot.on.message(func=payload_cmd("adm_player"))
    async def adm_player_ask(message: Message):
        if not await _require(message):
            return
        _pending[(message.peer_id, message.from_id)] = "player"
        await reply(
            message,
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
        await reply(
            message,
            f"{listing}\n\n"
            "Напиши название или id страны для удаления.\n"
            "Примеры: Тест  |  1  |  id=1",
            keyboard=cancel_keyboard().get_json(),
        )

    # --- extra moderation / gifts / fun ---
    @bot.on.message(func=payload_cmd("adm_jail"))
    async def adm_jail_ask(message: Message):
        if not await _require(message):
            return
        _pending[(message.peer_id, message.from_id)] = "jail"
        await reply(
            message,
            "⛓ Тюрьма. Формат: ID ЧАСЫ\nПример: 525336510 2",
            keyboard=cancel_keyboard().get_json(),
        )

    @bot.on.message(func=payload_cmd("adm_unjail"))
    async def adm_unjail_ask(message: Message):
        if not await _require(message):
            return
        _pending[(message.peer_id, message.from_id)] = "unjail"
        await reply(
            message,
            "🔓 VK ID игрока для освобождения:",
            keyboard=cancel_keyboard().get_json(),
        )

    @bot.on.message(func=payload_cmd("adm_take"))
    async def adm_take_ask(message: Message):
        if not await _require(message):
            return
        _pending[(message.peer_id, message.from_id)] = "take"
        await reply(
            message,
            "💸 Забрать кроны. Формат: ID СУММА",
            keyboard=cancel_keyboard().get_json(),
        )

    @bot.on.message(func=payload_cmd("adm_kick"))
    async def adm_kick_ask(message: Message):
        if not await _require(message):
            return
        _pending[(message.peer_id, message.from_id)] = "kick"
        await reply(
            message,
            "👢 VK ID игрока для кика из страны:",
            keyboard=cancel_keyboard().get_json(),
        )

    @bot.on.message(func=payload_cmd("adm_item"))
    async def adm_item_ask(message: Message):
        if not await _require(message):
            return
        _pending[(message.peer_id, message.from_id)] = "item"
        await reply(
            message,
            "📦 Формат: ID item_id [кол-во]\n"
            "Пример: 525336510 rusty_pick 1",
            keyboard=cancel_keyboard().get_json(),
        )

    @bot.on.message(func=payload_cmd("adm_title"))
    async def adm_title_ask(message: Message):
        if not await _require(message):
            return
        _pending[(message.peer_id, message.from_id)] = "title"
        codes = ", ".join(sorted(config.TITLE_LABELS.keys()))
        await reply(
            message,
            f"🏷 Формат: ID код_титула\nКоды: {codes}",
            keyboard=cancel_keyboard().get_json(),
        )

    @bot.on.message(func=payload_cmd("adm_energy_all"))
    async def adm_energy_all(message: Message):
        if not await _require(message):
            return
        async with SessionLocal() as session:
            try:
                r = await admin_svc.fill_energy_all(session)
            except AdminError as e:
                await reply(message, e.message, keyboard=admin_extra_keyboard().get_json())
                return
        await reply(
            message,
            f"⚡ Энергия полная у {r['count']} игроков ({r['energy']}).",
            keyboard=admin_extra_keyboard().get_json(),
        )

    @bot.on.message(func=payload_cmd("adm_cd_all"))
    async def adm_cd_all(message: Message):
        if not await _require(message):
            return
        async with SessionLocal() as session:
            r = await admin_svc.reset_cooldowns_all(session)
        await reply(
            message,
            f"⏱ КД сброшены у {r['count']} игроков.",
            keyboard=admin_extra_keyboard().get_json(),
        )

    @bot.on.message(func=payload_cmd("adm_top_rich"))
    async def adm_top_rich(message: Message):
        if not await _require(message):
            return
        async with SessionLocal() as session:
            text = await admin_svc.top_rich(session)
        await reply(message, text, keyboard=admin_extra_keyboard().get_json())

    @bot.on.message(func=payload_cmd("adm_find"))
    async def adm_find_ask(message: Message):
        if not await _require(message):
            return
        _pending[(message.peer_id, message.from_id)] = "find"
        await reply(
            message,
            "🔎 Часть имени игрока:",
            keyboard=cancel_keyboard().get_json(),
        )

    @bot.on.message(func=payload_cmd("adm_jackpot"))
    async def adm_jackpot_ask(message: Message):
        if not await _require(message):
            return
        _pending[(message.peer_id, message.from_id)] = "jackpot"
        await reply(
            message,
            "🎰 Джекпот случайному игроку.\nСумма крон:",
            keyboard=cancel_keyboard().get_json(),
        )

    @bot.on.message(func=payload_cmd("adm_rain"))
    async def adm_rain_ask(message: Message):
        if not await _require(message):
            return
        _pending[(message.peer_id, message.from_id)] = "rain"
        await reply(
            message,
            "🌧 Дождь крон в стране.\nФормат: Название СУММА\nПример: Тест 50",
            keyboard=cancel_keyboard().get_json(),
        )

    @bot.on.message(blocking=False)
    async def admin_text_flow(message: Message):
        if not is_admin(message.from_id) or not _dm_only(message):
            return

        text = (message.text or "").strip()
        if not text:
            return

        lower = text.casefold()
        if await _handle_commands(message, text, lower):
            return

        key = (message.peer_id, message.from_id)
        mode = _pending.get(key)
        if not mode:
            return
        if lower in {"отмена", "❌ отмена", "cancel"}:
            _pending.pop(key, None)
            _pending_event.pop(key, None)
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
                parts = text.split(maxsplit=1)
                await _do_give_all(
                    message, int(parts[0]), parts[1] if len(parts) >= 2 else ""
                )
            elif mode == "energy":
                await _do_energy(message, int(text.split()[0]))
            elif mode == "cd":
                await _do_cd(message, int(text.split()[0]))
            elif mode == "player":
                await _do_player(message, int(text.split()[0]))
            elif mode == "del_nation":
                await _do_del_nation(message, text)
            elif mode == "event_hours":
                ev_key = _pending_event.pop(key, None)
                if not ev_key:
                    await reply(
                        message,
                        "Ивент сброшен, выбери снова.",
                        keyboard=admin_events_keyboard().get_json(),
                    )
                    return
                hours = None
                raw = text.strip()
                if raw and raw not in {"-", ".", "default", "дефолт"}:
                    hours = float(raw.replace(",", "."))
                await _do_force_event(message, ev_key, hours)
            elif mode == "jail":
                parts = text.split()
                await _do_jail(message, int(parts[0]), float(parts[1].replace(",", ".")))
            elif mode == "unjail":
                await _do_unjail(message, int(text.split()[0]))
            elif mode == "take":
                parts = text.split()
                await _do_take(message, int(parts[0]), int(parts[1]))
            elif mode == "kick":
                await _do_kick(message, int(text.split()[0]))
            elif mode == "item":
                parts = text.split()
                qty = int(parts[2]) if len(parts) >= 3 else 1
                await _do_item(message, int(parts[0]), parts[1], qty)
            elif mode == "title":
                parts = text.split(maxsplit=1)
                await _do_title(message, int(parts[0]), parts[1].strip())
            elif mode == "find":
                await _do_find(message, text)
            elif mode == "jackpot":
                await _do_jackpot(message, int(text.split()[0]))
            elif mode == "rain":
                parts = text.rsplit(maxsplit=1)
                await _do_rain(message, parts[0], int(parts[1]))
        except (ValueError, IndexError):
            await reply(message, "Неверный формат.", keyboard=admin_keyboard().get_json())


async def _handle_commands(message: Message, text: str, lower: str) -> bool:
    """True если команда обработана."""
    if lower.startswith("!дать ") or lower.startswith("!give "):
        parts = text.split()
        if len(parts) >= 3 and parts[1].isdigit():
            await _do_give(message, int(parts[1]), int(parts[2]))
        else:
            await message.answer("Формат: !дать ID СУММА")
        return True
    if lower.startswith("!игрок ") or lower.startswith("!player "):
        parts = text.split()
        if len(parts) >= 2 and parts[1].isdigit():
            await _do_player(message, int(parts[1]))
        return True
    if lower.startswith("!кд ") or lower.startswith("!cd "):
        parts = text.split()
        if len(parts) >= 2 and parts[1].isdigit():
            await _do_cd(message, int(parts[1]))
        return True
    if lower.startswith("!энергия ") or lower.startswith("!energy "):
        parts = text.split()
        if len(parts) >= 2 and parts[1].isdigit():
            await _do_energy(message, int(parts[1]))
        return True
    if lower.startswith("!удалитьстрану ") or lower.startswith("!delnation "):
        await _do_del_nation(message, text.split(maxsplit=1)[1].strip())
        return True
    if lower.startswith("!объявление ") or lower.startswith("!broadcast "):
        await _do_broadcast(
            message, text.split(maxsplit=1)[1].strip(), to_chats=True, to_dms=True
        )
        return True
    if lower.startswith("!объявление_беседы "):
        await _do_broadcast(
            message, text.split(maxsplit=1)[1].strip(), to_chats=True, to_dms=False
        )
        return True
    if lower.startswith("!объявление_лс "):
        await _do_broadcast(
            message, text.split(maxsplit=1)[1].strip(), to_chats=False, to_dms=True
        )
        return True
    if lower.startswith("!принять ") or lower.startswith("!accept "):
        parts = text.split(maxsplit=1)
        if len(parts) >= 2 and parts[1].strip().split()[0].isdigit():
            await _do_accept(message, int(parts[1].strip().split()[0]))
        else:
            await reply(message, "Формат: !принять ID", keyboard=admin_keyboard().get_json())
        return True
    if lower.startswith("!отклонить ") or lower.startswith("!reject "):
        parts = text.split(maxsplit=2)
        if len(parts) >= 2 and parts[1].isdigit():
            await _do_reject(message, int(parts[1]), parts[2] if len(parts) >= 3 else "")
        else:
            await reply(
                message,
                "Формат: !отклонить ID [причина]",
                keyboard=admin_keyboard().get_json(),
            )
        return True
    if lower.startswith("!багпринять ") or lower.startswith("!bugaccept "):
        parts = text.split()
        if len(parts) >= 2 and parts[1].isdigit():
            await _do_accept_bug(message, int(parts[1]))
        else:
            await reply(
                message,
                "Формат: !багпринять ID",
                keyboard=admin_keyboard().get_json(),
            )
        return True
    if lower.startswith("!баготклонить ") or lower.startswith("!bugreject "):
        parts = text.split(maxsplit=2)
        if len(parts) >= 2 and parts[1].isdigit():
            await _do_reject_bug(
                message, int(parts[1]), parts[2] if len(parts) >= 3 else ""
            )
        else:
            await reply(
                message,
                "Формат: !баготклонить ID [причина]",
                keyboard=admin_keyboard().get_json(),
            )
        return True
    if lower.startswith("!всем ") or lower.startswith("!giveall "):
        parts = text.split(maxsplit=2)
        if len(parts) >= 2:
            try:
                amount = int(parts[1])
            except ValueError:
                amount = None
            if amount is not None:
                await _do_give_all(
                    message, amount, parts[2] if len(parts) >= 3 else ""
                )
            else:
                await reply(
                    message,
                    "Формат: !всем СУММА [текст]",
                    keyboard=admin_keyboard().get_json(),
                )
        return True
    if lower.startswith("!ивент ") or lower.startswith("!event "):
        parts = text.split()
        if len(parts) >= 2:
            hours = float(parts[2].replace(",", ".")) if len(parts) >= 3 else None
            await _do_force_event(message, parts[1].strip(), hours)
        else:
            keys = ", ".join(sorted(config.WORLD_EVENTS.keys()))
            await reply(
                message,
                f"Формат: !ивент KEY [часы]\nКлючи: {keys}",
                keyboard=admin_events_keyboard().get_json(),
            )
        return True
    if lower in {"!стоп_ивент", "!stop_event", "!ивент_стоп"}:
        await _do_stop_event(message)
        return True
    if lower.startswith("!вспышка ") or lower.startswith("!flash "):
        parts = text.split()
        # !вспышка | !вспышка KEY | !вспышка KEY 2
        key = None
        hours = None
        if len(parts) >= 2 and parts[1] not in {"стоп", "stop", "random", "случ", "★"}:
            key = parts[1].strip()
            if len(parts) >= 3:
                try:
                    hours = float(parts[2].replace(",", "."))
                except ValueError:
                    hours = None
        await _do_force_flash(message, key=key, hours=hours)
        return True
    if lower in {
        "!вспышка",
        "!flash",
        "!вспышка_случ",
        "!flash_rand",
    }:
        await _do_force_flash(message, key=None, hours=None)
        return True
    if lower in {"!вспышка_стоп", "!flash_stop", "!стоп_вспышка"}:
        await _do_stop_flash(message)
        return True
    if lower in {"!вспышки", "!flash_list"}:
        text_list = list_flashes_text()
        await reply(
            message,
            text_list[:3800],
            keyboard=admin_events_keyboard().get_json(),
        )
        return True
    if lower.startswith("!тюрьма ") or lower.startswith("!jail "):
        parts = text.split()
        if len(parts) >= 3 and parts[1].isdigit():
            await _do_jail(message, int(parts[1]), float(parts[2].replace(",", ".")))
        else:
            await reply(
                message,
                "Формат: !тюрьма ID ЧАСЫ",
                keyboard=admin_extra_keyboard().get_json(),
            )
        return True
    if lower.startswith("!свобода ") or lower.startswith("!unjail "):
        parts = text.split()
        if len(parts) >= 2 and parts[1].isdigit():
            await _do_unjail(message, int(parts[1]))
        return True
    if lower.startswith("!предмет ") or lower.startswith("!item "):
        parts = text.split()
        if len(parts) >= 3 and parts[1].isdigit():
            qty = int(parts[3]) if len(parts) >= 4 else 1
            await _do_item(message, int(parts[1]), parts[2], qty)
        else:
            await reply(
                message,
                "Формат: !предмет ID item_id [кол-во]",
                keyboard=admin_extra_keyboard().get_json(),
            )
        return True
    if lower.startswith("!титул ") or lower.startswith("!title "):
        parts = text.split(maxsplit=2)
        if len(parts) >= 3 and parts[1].isdigit():
            await _do_title(message, int(parts[1]), parts[2].strip())
        return True
    if lower.startswith("!джекпот ") or lower.startswith("!jackpot "):
        parts = text.split()
        if len(parts) >= 2:
            await _do_jackpot(message, int(parts[1]))
        return True
    if lower.startswith("!дождь ") or lower.startswith("!rain "):
        rest = text.split(maxsplit=1)[1]
        parts = rest.rsplit(maxsplit=1)
        if len(parts) == 2 and parts[1].isdigit():
            await _do_rain(message, parts[0], int(parts[1]))
        else:
            await reply(
                message,
                "Формат: !дождь Название СУММА",
                keyboard=admin_extra_keyboard().get_json(),
            )
        return True
    return False


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


async def _do_force_event(
    message: Message, key: str, hours: float | None = None
) -> None:
    if not await _require(message):
        return
    async with SessionLocal() as session:
        try:
            ev = await force_event(session, key, hours)
        except ValueError as e:
            await reply(
                message, str(e), keyboard=admin_events_keyboard().get_json()
            )
            return
    body = (
        f"🌤 Имперский ивент!\n\n"
        f"{ev['title']}\n{ev['desc']}\n\n"
        f"Длительность: ~{ev['hours']:.1f} ч.\n"
        f"Смотри «🌤 Ивент дня» в меню."
    )
    await reply(
        message,
        f"✅ Запущен: {format_event(ev)}\n⏳ Рассылка…",
        keyboard=admin_events_keyboard().get_json(),
    )
    async with SessionLocal() as session:
        try:
            report = await broadcast(
                message.ctx_api, session, body, to_chats=True, to_dms=True
            )
        except ValueError as e:
            await reply(message, str(e), keyboard=admin_events_keyboard().get_json())
            return
    await reply(
        message, format_report(report), keyboard=admin_events_keyboard().get_json()
    )


async def _do_stop_event(message: Message) -> None:
    if not await _require(message):
        return
    async with SessionLocal() as session:
        prev = await clear_event(session)
    if not prev:
        await reply(
            message,
            "Активного дневного ивента нет.",
            keyboard=admin_events_keyboard().get_json(),
        )
        return
    body = (
        f"⏹ Ивент дня завершён администратором.\n"
        f"Был: {prev.get('title', '?')}.\n"
        f"Снова обычный день (вспышки судьбы не тронуты)."
    )
    await reply(
        message,
        f"⏹ Остановлен: {prev.get('title')}\n⏳ Рассылка…",
        keyboard=admin_events_keyboard().get_json(),
    )
    async with SessionLocal() as session:
        try:
            report = await broadcast(
                message.ctx_api, session, body, to_chats=True, to_dms=True
            )
        except ValueError as e:
            await reply(message, str(e), keyboard=admin_events_keyboard().get_json())
            return
    await reply(
        message, format_report(report), keyboard=admin_events_keyboard().get_json()
    )


async def _do_force_flash(
    message: Message, key: str | None = None, hours: float | None = None
) -> None:
    if not await _require(message):
        return
    async with SessionLocal() as session:
        try:
            ev = await force_flash(session, key=key, hours=hours, forced=True)
        except ValueError as e:
            await reply(
                message, str(e), keyboard=admin_events_keyboard().get_json()
            )
            return
    body = format_flash_announce(ev)
    await reply(
        message,
        f"✅ Вспышка: {ev['title']}\n⏳ Рассылка…",
        keyboard=admin_events_keyboard().get_json(),
    )
    async with SessionLocal() as session:
        try:
            report = await broadcast(
                message.ctx_api, session, body, to_chats=True, to_dms=True
            )
        except ValueError as e:
            await reply(message, str(e), keyboard=admin_events_keyboard().get_json())
            return
    await reply(
        message, format_report(report), keyboard=admin_events_keyboard().get_json()
    )


async def _do_stop_flash(message: Message) -> None:
    if not await _require(message):
        return
    async with SessionLocal() as session:
        prev = await clear_flash(session)
    if not prev:
        await reply(
            message,
            "Активной вспышки нет.",
            keyboard=admin_events_keyboard().get_json(),
        )
        return
    body = (
        f"⏹ Вспышка судьбы погасла.\n"
        f"Была: {prev.get('title', '?')}."
    )
    await reply(
        message,
        f"⏹ Вспышка остановлена: {prev.get('title')}\n⏳ Рассылка…",
        keyboard=admin_events_keyboard().get_json(),
    )
    async with SessionLocal() as session:
        try:
            report = await broadcast(
                message.ctx_api, session, body, to_chats=True, to_dms=True
            )
        except ValueError as e:
            await reply(message, str(e), keyboard=admin_events_keyboard().get_json())
            return
    await reply(
        message, format_report(report), keyboard=admin_events_keyboard().get_json()
    )


async def _do_give(message: Message, vk_id: int, amount: int) -> None:
    async with SessionLocal() as session:
        try:
            p = await admin_svc.give_crowns(session, vk_id, amount)
        except AdminError as e:
            await reply(message, e.message, keyboard=admin_keyboard().get_json())
            return
        await reply(
            message,
            f"✅ {p.name} ({vk_id}): {amount:+d} крон → {p.crowns}",
            keyboard=admin_keyboard().get_json(),
        )


async def _do_give_all(message: Message, amount: int, note: str = "") -> None:
    if not await _require(message):
        return
    async with SessionLocal() as session:
        try:
            result = await admin_svc.give_crowns_all(session, amount)
        except AdminError as e:
            await reply(message, e.message, keyboard=admin_keyboard().get_json())
            return

    note = (note or "").strip()
    body = (
        f"🎁 Бонус за обновление!\n\n"
        f"Всем игрокам начислено {amount:+d} крон."
    )
    if note:
        body += f"\n\n{note}"
    else:
        body += "\n\nСпасибо, что играете в Империю чатов!"

    await reply(
        message,
        f"🎁 Начислено {amount:+d} × {result['count']} "
        f"(всего {result['total']:+d}).\n⏳ Рассылка…",
        keyboard=admin_keyboard().get_json(),
    )
    async with SessionLocal() as session:
        try:
            report = await broadcast(
                message.ctx_api, session, body, to_chats=True, to_dms=True
            )
        except ValueError as e:
            await reply(message, str(e), keyboard=admin_keyboard().get_json())
            return
    await reply(message, format_report(report), keyboard=admin_keyboard().get_json())


async def _do_energy(message: Message, vk_id: int) -> None:
    async with SessionLocal() as session:
        try:
            p = await admin_svc.fill_energy(session, vk_id)
        except AdminError as e:
            await reply(message, e.message, keyboard=admin_keyboard().get_json())
            return
        await reply(
            message,
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
        await reply(
            message,
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
            await reply(message, e.message, keyboard=admin_extra_keyboard().get_json())
            return
        await reply(
            message,
            f"🗑 Удалена страна {deleted}",
            keyboard=admin_extra_keyboard().get_json(),
        )


async def _do_jail(message: Message, vk_id: int, hours: float) -> None:
    async with SessionLocal() as session:
        try:
            p = await admin_svc.jail_player(session, vk_id, hours)
        except AdminError as e:
            await reply(message, e.message, keyboard=admin_extra_keyboard().get_json())
            return
    await reply(
        message,
        f"⛓ {p.name} в тюрьме на {hours} ч.",
        keyboard=admin_extra_keyboard().get_json(),
    )


async def _do_unjail(message: Message, vk_id: int) -> None:
    async with SessionLocal() as session:
        try:
            p = await admin_svc.unjail_player(session, vk_id)
        except AdminError as e:
            await reply(message, e.message, keyboard=admin_extra_keyboard().get_json())
            return
    await reply(
        message,
        f"🔓 {p.name} освобождён.",
        keyboard=admin_extra_keyboard().get_json(),
    )


async def _do_take(message: Message, vk_id: int, amount: int) -> None:
    async with SessionLocal() as session:
        try:
            p = await admin_svc.take_crowns(session, vk_id, amount)
        except AdminError as e:
            await reply(message, e.message, keyboard=admin_extra_keyboard().get_json())
            return
    await reply(
        message,
        f"💸 {p.name}: −{amount} → {p.crowns} крон",
        keyboard=admin_extra_keyboard().get_json(),
    )


async def _do_kick(message: Message, vk_id: int) -> None:
    async with SessionLocal() as session:
        try:
            r = await admin_svc.kick_from_nation(session, vk_id)
        except AdminError as e:
            await reply(message, e.message, keyboard=admin_extra_keyboard().get_json())
            return
    await reply(
        message,
        f"👢 {r['player'].name} кикнут из {r['nation']}.",
        keyboard=admin_extra_keyboard().get_json(),
    )


async def _do_item(message: Message, vk_id: int, item_id: str, qty: int) -> None:
    async with SessionLocal() as session:
        try:
            r = await admin_svc.give_item_to_player(session, vk_id, item_id, qty)
        except AdminError as e:
            await reply(message, e.message, keyboard=admin_extra_keyboard().get_json())
            return
    it = r["item"]
    await reply(
        message,
        f"📦 {r['player'].name}: +{r['qty']}× {it.get('name', item_id)}",
        keyboard=admin_extra_keyboard().get_json(),
    )


async def _do_title(message: Message, vk_id: int, code: str) -> None:
    async with SessionLocal() as session:
        try:
            r = await admin_svc.give_title_to_player(session, vk_id, code)
        except AdminError as e:
            await reply(message, e.message, keyboard=admin_extra_keyboard().get_json())
            return
    await reply(
        message,
        f"🏷 {r['player'].name}: титул «{r['title']}»",
        keyboard=admin_extra_keyboard().get_json(),
    )


async def _do_find(message: Message, query: str) -> None:
    async with SessionLocal() as session:
        try:
            text = await admin_svc.find_by_name(session, query)
        except AdminError as e:
            await reply(message, e.message, keyboard=admin_extra_keyboard().get_json())
            return
    await reply(message, text, keyboard=admin_extra_keyboard().get_json())


async def _do_jackpot(message: Message, amount: int) -> None:
    if not await _require(message):
        return
    async with SessionLocal() as session:
        try:
            r = await admin_svc.jackpot_random(session, amount)
        except AdminError as e:
            await reply(message, e.message, keyboard=admin_extra_keyboard().get_json())
            return
        winner = r["player"]
        name = winner.name
        vk_id = winner.vk_id
        crowns = winner.crowns
    body = (
        f"🎰 Джекпот Империи!\n\n"
        f"Победитель: {name}\n"
        f"Выигрыш: +{amount} крон!"
    )
    await reply(
        message,
        f"🎰 {name} (id{vk_id}): +{amount} → {crowns}\n⏳ Анонс…",
        keyboard=admin_extra_keyboard().get_json(),
    )
    async with SessionLocal() as session:
        try:
            report = await broadcast(
                message.ctx_api, session, body, to_chats=True, to_dms=True
            )
        except ValueError as e:
            await reply(message, str(e), keyboard=admin_extra_keyboard().get_json())
            return
    await reply(
        message, format_report(report), keyboard=admin_extra_keyboard().get_json()
    )


async def _do_rain(message: Message, nation_name: str, amount: int) -> None:
    if not await _require(message):
        return
    async with SessionLocal() as session:
        try:
            r = await admin_svc.nation_rain(session, nation_name, amount)
        except AdminError as e:
            await reply(message, e.message, keyboard=admin_extra_keyboard().get_json())
            return
        nation = r["nation"]
        peer_id = r["peer_id"]
        count = r["count"]
        total = r["total"]
        flag = nation.flag_emoji
        name = nation.name
    await reply(
        message,
        f"🌧 {flag} {name}: +{amount} ×{count} (всего {total})",
        keyboard=admin_extra_keyboard().get_json(),
    )
    chat_msg = (
        f"🌧 Имперский дождь крон!\n"
        f"Каждому гражданину {flag} {name}: +{amount} крон."
    )
    try:
        await message.ctx_api.messages.send(
            peer_id=peer_id,
            message=chat_msg,
            random_id=random.randint(1, 2_000_000_000),
        )
    except Exception:
        pass


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


async def _do_accept_bug(message: Message, bug_id: int) -> None:
    if not await _require(message):
        return
    async with SessionLocal() as session:
        try:
            result = await accept_bug(session, bug_id)
        except BugError as e:
            await reply(message, e.message, keyboard=admin_keyboard().get_json())
            return
        bug = result["bug"]
        reward = result["reward"]
        author_id = bug.author_vk_id
        author_name = bug.author_name
        body = bug.text
        crowns = result["crowns"]

    dm = (
        f"✅ Твой багрепорт #{bug_id} подтверждён!\n\n"
        f"«{body}»\n\n"
        f"Награда: +{reward} крон"
        + (f" (баланс {crowns})." if crowns is not None else ".")
        + "\nСпасибо — баг взят в работу."
    )
    dm_ok = await _notify_author(message, author_id, dm)
    await reply(
        message,
        f"🐛 #{bug_id} подтверждён · {author_name}\n"
        f"+{reward} крон автору"
        + (" · ЛС отправлено" if dm_ok else " · ЛС не доставлено"),
        keyboard=admin_keyboard().get_json(),
    )


async def _do_reject_bug(message: Message, bug_id: int, note: str = "") -> None:
    if not await _require(message):
        return
    async with SessionLocal() as session:
        try:
            result = await reject_bug(session, bug_id, note)
        except BugError as e:
            await reply(message, e.message, keyboard=admin_keyboard().get_json())
            return
        bug = result["bug"]
        author_id = bug.author_vk_id
        author_name = bug.author_name
        body = bug.text
        reason = (note or "").strip()

    dm = f"❌ Багрепорт #{bug_id} отклонён.\n\n«{body}»"
    if reason:
        dm += f"\n\nПричина: {reason}"
    dm_ok = await _notify_author(message, author_id, dm)
    await reply(
        message,
        f"🐛 #{bug_id} отклонён · {author_name}"
        + (f"\nПричина: {reason}" if reason else "")
        + (" · ЛС отправлено" if dm_ok else " · ЛС не доставлено"),
        keyboard=admin_keyboard().get_json(),
    )
