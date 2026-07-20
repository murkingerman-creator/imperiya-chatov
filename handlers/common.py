"""Тексты меню, приветствия в беседе и подробный гайд."""

import logging
import random

from vkbottle import Keyboard
from vkbottle.bot import Message

from bot.config import is_admin
from bot.keyboards import main_keyboard
from db.database import SessionLocal
from services.player import get_or_create_player

logger = logging.getLogger("empire.reply")

CHAT_PEER_OFFSET = 2_000_000_000
EMPTY_KEYBOARD = Keyboard(one_time=True).get_json()

# Последняя беседа, из которой игрок жал кнопки (для «Основать» / «Вступить» из ЛС)
_LAST_CHAT_PEER: dict[int, int] = {}


def is_chat_peer(peer_id: int) -> bool:
    return peer_id >= CHAT_PEER_OFFSET


def remember_chat_peer(message: Message) -> None:
    if is_chat_peer(message.peer_id):
        _LAST_CHAT_PEER[message.from_id] = message.peer_id


def resolve_chat_peer(message: Message) -> int | None:
    """Peer беседы: текущий чат или последний, откуда открывали меню."""
    if is_chat_peer(message.peer_id):
        return message.peer_id
    return _LAST_CHAT_PEER.get(message.from_id)


MENU_TEXT = (
    "🏛 Империя чатов\n\n"
    "Беседа = государство. Работай, строй казну, воюй, зови друзей.\n\n"
    "• 🎁 Ежедневка · 💼 Работа (+контрабанда, лут)\n"
    "• 🎒 Сумка · 🏪 Лавка (быт / война / престиж)\n"
    "• 🏛 Страна · Казна · Цель · Роли\n"
    "• ⚔ Рейды · 🎲 Дуэль · 🏆 Сезон · 🎯 Ещё\n"
    "• 📖 Как играть — полный гайд\n\n"
    "⚠ Личное меню — в ЛС с ботом (в беседе клавиатура общая).\n"
    "Добавь бота в беседу, чтобы основать страну."
)

WELCOME_CHAT_TEXT = (
    "🏛 Империя чатов уже в вашей беседе!\n\n"
    "Здесь беседа становится государством: казна, граждане, рейды и война с другими чатами.\n\n"
    "Что сделать сейчас:\n"
    "1) Каждый пишет боту в ЛС «Начать» — личное меню только там\n"
    "2) В беседе: «Страна» (ответ придёт в ЛС) → основать страну\n"
    "3) Работайте, копите казну, зовите друзей инвайтом\n\n"
    "⚠ В беседе не играйте кнопками «за всех» — меню личное, открывайте ЛС.\n"
    "📖 Гайд — «Как играть» в ЛС.\n"
    "Удачи. Пусть ваша беседа станет империей."
)

# VK limit ~4096; split into parts for reliability
GUIDE_PARTS = [
    (
        "📖 Как играть — Империя чатов\n\n"
        "Суть: одна беседа ВК = одна страна. "
        "Игроки зарабатывают кроны, наполняют казну, собирают предметы, "
        "рейдят чужие государства и спорят за лидерство.\n\n"
        "⚠ Важно: личные кнопки (работа, сумка, профиль) — "
        "только в ЛС с ботом. В беседе клавиатура общая на всех.\n\n"
        "─── С чего начать ───\n"
        "1. Напиши боту в ЛС «Начать» — квест новичка: ежедневка → работа → страна.\n"
        "2. Добавь бота в беседу (если ещё нет).\n"
        "3. «🏛 Страна» → «Основать страну» "
        "(нужны кроны на основание; лидер = основатель).\n"
        "4. Друзья: «📨 Инвайт» — дай код. Друг пишет: инвайт КОД "
        "(бонусы вам обоим и казне).\n"
        "5. Каждый день: «🎁 Ежедневка» — стрик крон.\n"
    ),
    (
        "─── Экономика ───\n"
        "👤 Профиль — кроны, энергия, титулы, экип, кодекс предметов.\n"
        "💼 Работа 2.0 — наборы из 📦 Привоза (ресток каждые 2ч), износ,\n"
        "  заказы дня, путь мастерства, смена дня (×2), слухи, бригада.\n"
        "  Тяжёлые работы без набора нельзя; лёгкие — можно (−40%, без лута).\n"
        "  У каждой работы своя механика; ранги профессий → бонус.\n"
        "  5 смен страны/час → 🐪 караван; 3 игрока на одной работе → 👷 бригада.\n"
        "  🕶 Контрабанда — нужен kit_cloak; ×3 или штраф и тюрьма.\n"
        "⚡ Энергия тратится на работы; восстанавливается со временем.\n"
        "🏪 Лавка — кроны по ролям: 🏠 Быт · ⚔ Война · 👑 Престиж "
        "(подношение, лицензия, наёмник, колесо). Из профиля: «Тратить кроны».\n"
        "В профиле видно личные кроны и налог в казну за неделю.\n"
        "🎒 Сумка — продажа ×1 / все, «Слить хлам» (common/uncommon, без инструментов).\n"
        "🏛 Казна (лидер/казначей) — указы, раздача, амнистия, щит осады.\n"
        "📅 Цель недели — общая задача страны → награда в казну.\n"
        "🏛 Налог страны забирает долю в казну (настраивает лидер).\n"
        "📦 Квест (Ещё) — сделай несколько работ → сундук с кронами.\n"
    ),
    (
        "─── Страна и война ───\n"
        "🏛 Страна — инфо, вступить, выйти, оформить (флаг, герб, гимн…), "
        "передать трон, распустить.\n"
        "🎭 Эмоции — праздник / к бою / гимн / траур в беседу страны.\n"
        "⚔ Война / Рейд — лидер или воевода. Шанс зависит от активных 👥 "
        "(работали/писали за 48ч) и экипа; в меню виден ~шанс. Малая страна может отбить.\n"
        "🛡 Щит казны — граждане скидываются, лидер активирует (−шанс рейда 24ч).\n"
        "🏆 Сезон — месячные очки за рейды и войны бесед; титул топ-странам.\n"
        "⚔ Война бесед (Ещё) — официальный матч двух стран на срок; "
        "очки за рейды; анонс и итог.\n"
        "🎲 Дуэль — ставка крон, КНБ или угадай число (удобно в беседе).\n"
        "🌤 Ивент дня — чума / ярмарка / восстание / жила / ночь рейдов "
        "(пятница): меняет доход и рейды на сутки.\n"
        "🗳 Выборы — граждане голосуют за лидера раз в неделю.\n"
    ),
    (
        "─── Арсенал и торг ───\n"
        "С работ и рейдов падают предметы разной редкости.\n"
        "🎒 Сумка — экип (инструмент / оружие / реликвия), кодекс, заряды.\n"
        "Легендарки и мифы дают уникальные заряды и ауры — не только «+%».\n"
        "💰 Продать боту — с подтверждением и ценой.\n"
        "⚒ Заточка — экип + дубликат + кроны → сильнее бонусы (до +3).\n"
        "🛒 Торг — выставь лот игрокам; фильтр по редкости; «найти …».\n"
        "🏷 Аукцион — трофеи после рейдов, ставки лидеров.\n\n"
        "─── Топы и админ ───\n"
        "🏆 Топ стран · 💰 Топ игроков · 🏆 Сезон.\n"
        "Хроника мира и короткие новости уходят на стену группы.\n\n"
        "Команды-кнопки всегда в «📋 Меню» (в ЛС). Удачной империи!"
    ),
]


def user_keyboard(vk_id: int) -> str:
    return main_keyboard(is_admin=is_admin(vk_id)).get_json()


async def reply(
    message: Message,
    text: str,
    keyboard: str | None = None,
) -> None:
    """
    Личный ответ с клавиатурой.
    В беседе reply-клавиатура общая на всех — поэтому меню уходит в ЛС,
    а в чат только короткое уведомление без кнопок.
    """
    remember_chat_peer(message)
    if not is_chat_peer(message.peer_id):
        kwargs = {}
        if keyboard is not None:
            kwargs["keyboard"] = keyboard
        await message.answer(text, **kwargs)
        return

    # Беседа: не вешаем личную клавиатуру на общий чат
    sent_dm = False
    try:
        send_kwargs = {
            "user_id": message.from_id,
            "message": text,
            "random_id": random.randint(1, 2_000_000_000),
        }
        if keyboard is not None:
            send_kwargs["keyboard"] = keyboard
        await message.ctx_api.messages.send(**send_kwargs)
        sent_dm = True
    except Exception as e:
        logger.info("DM failed for %s: %s", message.from_id, e)

    if sent_dm:
        await message.answer(
            f"[id{message.from_id}|Игрок], ответ в личных сообщениях с ботом.\n"
            f"(В беседе кнопки общие — играй в ЛС.)",
            keyboard=EMPTY_KEYBOARD,
        )
    elif keyboard is not None:
        await message.answer(
            f"[id{message.from_id}|Игрок], не могу написать в ЛС.\n"
            f"Открой диалог с ботом сообщества → «Начать», разреши сообщения.\n"
            f"Иначе кнопки в беседе будут общие на всех.",
            keyboard=EMPTY_KEYBOARD,
        )
    else:
        # Текст без кнопок — можно показать в беседе
        await message.answer(text, keyboard=EMPTY_KEYBOARD)


async def reply_chat(message: Message, text: str) -> None:
    """Публичный ответ в беседу без клавиатуры (эмоции, анонсы)."""
    await message.answer(text, keyboard=EMPTY_KEYBOARD)


async def reply_here(
    message: Message,
    text: str,
    keyboard: str | None = None,
) -> None:
    """
    Ответ в тот же peer (беседа или ЛС).
    Для inline-кнопок (дуэли): не уводит в ЛС и не трогает общую reply-клавиатуру.
    """
    if keyboard is not None:
        await message.answer(text, keyboard=keyboard)
    else:
        await message.answer(text, keyboard=EMPTY_KEYBOARD)


async def resolve_name(message: Message) -> str:
    try:
        users = await message.ctx_api.users.get(user_ids=[message.from_id])
        if users:
            u = users[0]
            return f"{u.first_name} {u.last_name}".strip()
    except Exception:
        pass
    return f"Игрок {message.from_id}"


async def ensure_player(message: Message):
    name = await resolve_name(message)
    async with SessionLocal() as session:
        player = await get_or_create_player(session, message.from_id, name)
        await session.commit()
        return player
