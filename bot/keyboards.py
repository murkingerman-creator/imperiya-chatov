from vkbottle import Keyboard, KeyboardButtonColor, Text

from bot import config
import json


def _inline_json(kb: Keyboard) -> str:
    """VK запрещает поле one_time у inline-клавиатур."""
    data = json.loads(kb.get_json())
    data.pop("one_time", None)
    return json.dumps(data, ensure_ascii=False)


def profile_keyboard() -> Keyboard:
    kb = Keyboard(one_time=False, inline=False)
    kb.add(
        Text("🏪 Тратить кроны", {"cmd": "profile_spend"}),
        color=KeyboardButtonColor.POSITIVE,
    )
    kb.add(Text("🎒 Сумка", {"cmd": "bag"}), color=KeyboardButtonColor.PRIMARY)
    kb.row()
    kb.add(Text("📋 Меню", {"cmd": "menu"}), color=KeyboardButtonColor.SECONDARY)
    return kb


def main_keyboard(*, is_admin: bool = False) -> Keyboard:
    kb = Keyboard(one_time=False, inline=False)
    kb.add(Text("👤 Профиль", {"cmd": "profile"}), color=KeyboardButtonColor.PRIMARY)
    kb.add(Text("🎁 Ежедневка", {"cmd": "daily"}), color=KeyboardButtonColor.POSITIVE)
    kb.row()
    kb.add(Text("💼 Работа", {"cmd": "jobs"}), color=KeyboardButtonColor.POSITIVE)
    kb.add(Text("🏛 Страна", {"cmd": "nation"}), color=KeyboardButtonColor.PRIMARY)
    kb.row()
    kb.add(Text("⚔ Война", {"cmd": "war"}), color=KeyboardButtonColor.NEGATIVE)
    kb.add(Text("🎲 Дуэль", {"cmd": "duel_menu"}), color=KeyboardButtonColor.NEGATIVE)
    kb.row()
    kb.add(Text("🎭 Эмоции", {"cmd": "emotions"}), color=KeyboardButtonColor.PRIMARY)
    kb.add(Text("📨 Инвайт", {"cmd": "invite"}), color=KeyboardButtonColor.SECONDARY)
    kb.row()
    kb.add(Text("🏆 Топ", {"cmd": "top_nations"}), color=KeyboardButtonColor.SECONDARY)
    kb.add(Text("🎒 Сумка", {"cmd": "bag"}), color=KeyboardButtonColor.PRIMARY)
    kb.row()
    kb.add(Text("🏪 Лавка", {"cmd": "shop"}), color=KeyboardButtonColor.POSITIVE)
    kb.add(Text("🎯 Ещё", {"cmd": "more"}), color=KeyboardButtonColor.SECONDARY)
    kb.row()
    kb.add(Text("📖 Как играть", {"cmd": "guide"}), color=KeyboardButtonColor.PRIMARY)
    kb.add(Text("📋 Меню", {"cmd": "menu"}), color=KeyboardButtonColor.SECONDARY)
    if is_admin:
        kb.add(Text("🛠 Админ", {"cmd": "admin"}), color=KeyboardButtonColor.PRIMARY)
    return kb


def onboarding_keyboard(step: int) -> Keyboard:
    kb = Keyboard(one_time=False, inline=False)
    if step == 1:
        kb.add(Text("🎁 Ежедневка", {"cmd": "daily"}), color=KeyboardButtonColor.POSITIVE)
    elif step == 2:
        kb.add(Text("💼 Работа", {"cmd": "jobs"}), color=KeyboardButtonColor.POSITIVE)
    elif step == 3:
        kb.add(Text("🏛 Страна", {"cmd": "nation"}), color=KeyboardButtonColor.PRIMARY)
        kb.add(Text("📨 Инвайт", {"cmd": "invite"}), color=KeyboardButtonColor.SECONDARY)
    kb.row()
    kb.add(Text("📋 Меню", {"cmd": "menu"}), color=KeyboardButtonColor.SECONDARY)
    return kb


def more_keyboard() -> Keyboard:
    kb = Keyboard(one_time=False, inline=False)
    kb.add(Text("🌤 Ивент дня", {"cmd": "world_event"}), color=KeyboardButtonColor.PRIMARY)
    kb.add(Text("📦 Квест", {"cmd": "quest"}), color=KeyboardButtonColor.POSITIVE)
    kb.row()
    kb.add(Text("🏷 Аукцион", {"cmd": "auction"}), color=KeyboardButtonColor.SECONDARY)
    kb.add(Text("🛒 Торг", {"cmd": "market"}), color=KeyboardButtonColor.POSITIVE)
    kb.row()
    kb.add(Text("🏪 Лавка", {"cmd": "shop"}), color=KeyboardButtonColor.POSITIVE)
    kb.add(Text("⚔ Война бесед", {"cmd": "chatwar"}), color=KeyboardButtonColor.NEGATIVE)
    kb.row()
    kb.add(Text("🗳 Выборы", {"cmd": "election"}), color=KeyboardButtonColor.PRIMARY)
    kb.add(Text("🏆 Сезон", {"cmd": "season"}), color=KeyboardButtonColor.POSITIVE)
    kb.row()
    kb.add(Text("📅 Цель недели", {"cmd": "weekly"}), color=KeyboardButtonColor.PRIMARY)
    kb.add(Text("💰 Топ игроков", {"cmd": "top_players"}), color=KeyboardButtonColor.SECONDARY)
    kb.row()
    kb.add(Text("🗺 Континент", {"cmd": "continent"}), color=KeyboardButtonColor.PRIMARY)
    kb.add(Text("📖 Сага", {"cmd": "saga"}), color=KeyboardButtonColor.POSITIVE)
    kb.row()
    kb.add(Text("📜 Контракты", {"cmd": "contracts"}), color=KeyboardButtonColor.SECONDARY)
    kb.add(Text("🕶 Чёрный рынок", {"cmd": "black_market"}), color=KeyboardButtonColor.NEGATIVE)
    kb.row()
    kb.add(Text("💡 Предложение", {"cmd": "suggest"}), color=KeyboardButtonColor.POSITIVE)
    kb.add(Text("🐛 Баг", {"cmd": "bug"}), color=KeyboardButtonColor.NEGATIVE)
    kb.row()
    kb.add(Text("📖 Как играть", {"cmd": "guide"}), color=KeyboardButtonColor.PRIMARY)
    kb.add(Text("📋 Меню", {"cmd": "menu"}), color=KeyboardButtonColor.SECONDARY)
    return kb


def shop_keyboard(*, jailed: bool = False) -> Keyboard:
    """Корень лавки: роли крон."""
    kb = Keyboard(one_time=False, inline=False)
    kb.add(
        Text("🏠 Быт", {"cmd": "shop_cat", "cat": "byt"}),
        color=KeyboardButtonColor.POSITIVE,
    )
    kb.add(
        Text("⚔ Война", {"cmd": "shop_cat", "cat": "war"}),
        color=KeyboardButtonColor.NEGATIVE,
    )
    kb.row()
    kb.add(
        Text("👑 Престиж", {"cmd": "shop_cat", "cat": "prestige"}),
        color=KeyboardButtonColor.PRIMARY,
    )
    if jailed:
        kb.add(
            Text("🔓 Выкуп", {"cmd": "shop_buy", "item": "bail"}),
            color=KeyboardButtonColor.POSITIVE,
        )
    kb.row()
    kb.add(Text("📋 Меню", {"cmd": "menu"}), color=KeyboardButtonColor.SECONDARY)
    return kb


def shop_byt_keyboard(*, jailed: bool = False) -> Keyboard:
    kb = Keyboard(one_time=False, inline=False)
    if jailed:
        kb.add(
            Text("🔓 Выкуп", {"cmd": "shop_buy", "item": "bail"}),
            color=KeyboardButtonColor.POSITIVE,
        )
        kb.row()
    kb.add(
        Text("⚡ Эликсир", {"cmd": "shop_buy", "item": "energy"}),
        color=KeyboardButtonColor.PRIMARY,
    )
    kb.add(
        Text("🍀 Удача", {"cmd": "shop_buy", "item": "work_luck"}),
        color=KeyboardButtonColor.POSITIVE,
    )
    kb.row()
    kb.add(Text("📦 Привоз", {"cmd": "supply"}), color=KeyboardButtonColor.POSITIVE)
    if not jailed:
        kb.add(
            Text("🔓 Выкуп", {"cmd": "shop_buy", "item": "bail"}),
            color=KeyboardButtonColor.SECONDARY,
        )
    kb.row()
    kb.add(Text("« Лавка", {"cmd": "shop"}), color=KeyboardButtonColor.SECONDARY)
    return kb


def shop_war_keyboard() -> Keyboard:
    kb = Keyboard(one_time=False, inline=False)
    kb.add(
        Text("⚔ Знамя", {"cmd": "shop_buy", "item": "raid_bless"}),
        color=KeyboardButtonColor.NEGATIVE,
    )
    kb.add(
        Text("🗡 Наёмник", {"cmd": "shop_buy", "item": "hire_blade"}),
        color=KeyboardButtonColor.PRIMARY,
    )
    kb.row()
    kb.add(
        Text("🛡 Щит", {"cmd": "tr_spend", "action": "shield_pay"}),
        color=KeyboardButtonColor.PRIMARY,
    )
    kb.add(Text("🏪 Лавка", {"cmd": "shop"}), color=KeyboardButtonColor.SECONDARY)
    return kb


def shop_prestige_keyboard() -> Keyboard:
    kb = Keyboard(one_time=False, inline=False)
    kb.add(
        Text("🏛 В казну", {"cmd": "shop_buy", "item": "treasury"}),
        color=KeyboardButtonColor.PRIMARY,
    )
    kb.add(
        Text("🕯 Подношение", {"cmd": "shop_buy", "item": "tribute"}),
        color=KeyboardButtonColor.POSITIVE,
    )
    kb.row()
    kb.add(
        Text("📜 Лицензия", {"cmd": "shop_buy", "item": "craft_license"}),
        color=KeyboardButtonColor.PRIMARY,
    )
    kb.add(
        Text("🎰 Колесо", {"cmd": "shop_buy", "item": "wheel"}),
        color=KeyboardButtonColor.POSITIVE,
    )
    kb.row()
    kb.add(Text("🏪 Лавка", {"cmd": "shop"}), color=KeyboardButtonColor.SECONDARY)
    return kb


def emotions_keyboard() -> Keyboard:
    kb = Keyboard(one_time=True, inline=False)
    kb.add(Text("🎉 Праздник", {"cmd": "emo", "kind": "party"}), color=KeyboardButtonColor.POSITIVE)
    kb.add(Text("⚔ К бою!", {"cmd": "emo", "kind": "war"}), color=KeyboardButtonColor.NEGATIVE)
    kb.row()
    kb.add(Text("🎵 Гимн", {"cmd": "emo", "kind": "anthem"}), color=KeyboardButtonColor.PRIMARY)
    kb.add(Text("😢 Траур", {"cmd": "emo", "kind": "sad"}), color=KeyboardButtonColor.SECONDARY)
    kb.row()
    kb.add(Text("📋 Меню", {"cmd": "menu"}), color=KeyboardButtonColor.SECONDARY)
    return kb


def duel_menu_keyboard() -> Keyboard:
    kb = Keyboard(one_time=False, inline=False)
    kb.add(Text("✊ КНБ 50", {"cmd": "duel_create", "mode": "rps", "bet": 50}))
    kb.add(Text("✊ КНБ 100", {"cmd": "duel_create", "mode": "rps", "bet": 100}))
    kb.row()
    kb.add(Text("🔢 Число 50", {"cmd": "duel_create", "mode": "number", "bet": 50}))
    kb.add(Text("🔢 Число 100", {"cmd": "duel_create", "mode": "number", "bet": 100}))
    kb.row()
    kb.add(Text("📋 Меню", {"cmd": "menu"}), color=KeyboardButtonColor.SECONDARY)
    return kb


def duel_accept_keyboard(token: str) -> str:
    # inline — в беседе не подменяет общую reply-клавиатуру
    kb = Keyboard(one_time=False, inline=True)
    kb.add(
        Text("✅ Принять дуэль", {"cmd": "duel_accept", "token": token}),
        color=KeyboardButtonColor.POSITIVE,
    )
    return _inline_json(kb)


def rps_keyboard(token: str) -> str:
    kb = Keyboard(one_time=False, inline=True)
    for label, move in [("✊ Камень", "rock"), ("✋ Бумага", "paper"), ("✌ Ножницы", "scissors")]:
        kb.add(Text(label, {"cmd": "duel_move", "token": token, "move": move}))
    return _inline_json(kb)


def number_keyboard(token: str) -> str:
    kb = Keyboard(one_time=False, inline=True)
    for n in range(1, 6):
        kb.add(Text(str(n), {"cmd": "duel_move", "token": token, "move": str(n)}))
        if n == 3:
            kb.row()
    return _inline_json(kb)


def auction_keyboard(auctions: list) -> Keyboard:
    kb = Keyboard(one_time=True, inline=False)
    for i, a in enumerate(auctions[:6]):
        if i and i % 2 == 0:
            kb.row()
        nxt = a.bid + 25
        kb.add(
            Text(f"#{a.id} →{nxt}", {"cmd": "auction_bid", "id": a.id, "amount": nxt}),
            color=KeyboardButtonColor.POSITIVE,
        )
    kb.row()
    kb.add(Text("🎯 Ещё", {"cmd": "more"}), color=KeyboardButtonColor.SECONDARY)
    return kb


def election_citizens_keyboard(citizens: list) -> Keyboard:
    kb = Keyboard(one_time=True, inline=False)
    for i, p in enumerate(citizens[:8]):
        if i and i % 2 == 0:
            kb.row()
        kb.add(
            Text(p.name[:18] or str(p.vk_id), {"cmd": "election_vote", "vk_id": p.vk_id}),
            color=KeyboardButtonColor.PRIMARY,
        )
    kb.row()
    kb.add(Text("🏁 Завершить", {"cmd": "election_finish"}), color=KeyboardButtonColor.POSITIVE)
    kb.add(Text("🎯 Ещё", {"cmd": "more"}), color=KeyboardButtonColor.SECONDARY)
    return kb


def chatwar_targets_keyboard(names: list[str]) -> Keyboard:
    kb = Keyboard(one_time=True, inline=False)
    for i, name in enumerate(names[:6]):
        if i and i % 2 == 0:
            kb.row()
        kb.add(
            Text(f"⚔ {name}", {"cmd": "chatwar_start", "target": name}),
            color=KeyboardButtonColor.NEGATIVE,
        )
    kb.row()
    kb.add(Text("🎯 Ещё", {"cmd": "more"}), color=KeyboardButtonColor.SECONDARY)
    return kb


def admin_keyboard() -> Keyboard:
    kb = Keyboard(one_time=False, inline=False)
    kb.add(Text("📊 Стата", {"cmd": "adm_stats"}), color=KeyboardButtonColor.PRIMARY)
    kb.add(Text("🏛 Список стран", {"cmd": "adm_nations"}), color=KeyboardButtonColor.SECONDARY)
    kb.row()
    kb.add(Text("💰 Дать кроны", {"cmd": "adm_give"}), color=KeyboardButtonColor.POSITIVE)
    kb.add(Text("⚡ Энергия", {"cmd": "adm_energy"}), color=KeyboardButtonColor.POSITIVE)
    kb.row()
    kb.add(Text("🔎 Игрок", {"cmd": "adm_player"}), color=KeyboardButtonColor.SECONDARY)
    kb.add(Text("⏱ Сброс КД", {"cmd": "adm_cd"}), color=KeyboardButtonColor.PRIMARY)
    kb.row()
    kb.add(Text("📣✉️ Везде", {"cmd": "adm_bcast_all"}), color=KeyboardButtonColor.POSITIVE)
    kb.add(Text("🎁 Всем кроны", {"cmd": "adm_give_all"}), color=KeyboardButtonColor.POSITIVE)
    kb.row()
    kb.add(Text("🌤 Ивенты", {"cmd": "adm_events"}), color=KeyboardButtonColor.PRIMARY)
    kb.add(Text("🎮 Ещё", {"cmd": "adm_extra"}), color=KeyboardButtonColor.PRIMARY)
    kb.row()
    kb.add(Text("💡 Предложения", {"cmd": "adm_suggestions"}), color=KeyboardButtonColor.PRIMARY)
    kb.add(Text("🐛 Баги", {"cmd": "adm_bugs"}), color=KeyboardButtonColor.NEGATIVE)
    kb.row()
    kb.add(Text("📋 Меню", {"cmd": "menu"}), color=KeyboardButtonColor.SECONDARY)
    return kb


def admin_events_keyboard() -> Keyboard:
    """Запуск мировых ивентов. Payload: adm_ev + key."""
    kb = Keyboard(one_time=False, inline=False)
    # row pairs of event launch buttons (short labels)
    buttons = [
        ("🕷 Чума", "plague"),
        ("🎪 Ярмарка", "fair"),
        ("🔥 Восстание", "revolt"),
        ("✨ Жила", "gold_vein"),
        ("🌙 Ночь рейдов", "raid_night"),
        ("🌾 Урожай", "harvest"),
        ("🩸 Кровавая луна", "blood_moon"),
        ("🕊 Мир", "peace"),
        ("🏛 Без налога", "tax_free"),
        ("💎 Дождь лута", "loot_rain"),
        ("🕶 Теневой рынок", "shadow_market"),
        ("🥀 Голод", "famine"),
        ("🛒 Купец", "merchant"),
    ]
    for i, (label, key) in enumerate(buttons):
        if i and i % 2 == 0:
            kb.row()
        kb.add(
            Text(label, {"cmd": "adm_ev", "key": key}),
            color=KeyboardButtonColor.PRIMARY,
        )
    kb.row()
    kb.add(Text("📡 Текущий", {"cmd": "adm_ev_status"}), color=KeyboardButtonColor.SECONDARY)
    kb.add(Text("⏹ Стоп день", {"cmd": "adm_ev_stop"}), color=KeyboardButtonColor.NEGATIVE)
    kb.row()
    kb.add(Text("⚡ Вспышка ★", {"cmd": "adm_flash_rand"}), color=KeyboardButtonColor.POSITIVE)
    kb.add(Text("⚡ Список", {"cmd": "adm_flash_list"}), color=KeyboardButtonColor.PRIMARY)
    kb.row()
    kb.add(Text("⚡ Стоп вспышки", {"cmd": "adm_flash_stop"}), color=KeyboardButtonColor.NEGATIVE)
    kb.add(Text("« Назад", {"cmd": "admin"}), color=KeyboardButtonColor.SECONDARY)
    return kb


def admin_extra_keyboard() -> Keyboard:
    kb = Keyboard(one_time=False, inline=False)
    kb.add(Text("⛓ Тюрьма", {"cmd": "adm_jail"}), color=KeyboardButtonColor.NEGATIVE)
    kb.add(Text("🔓 Свобода", {"cmd": "adm_unjail"}), color=KeyboardButtonColor.POSITIVE)
    kb.row()
    kb.add(Text("💸 Забрать кроны", {"cmd": "adm_take"}), color=KeyboardButtonColor.NEGATIVE)
    kb.add(Text("👢 Кик из страны", {"cmd": "adm_kick"}), color=KeyboardButtonColor.NEGATIVE)
    kb.row()
    kb.add(Text("📦 Предмет", {"cmd": "adm_item"}), color=KeyboardButtonColor.PRIMARY)
    kb.add(Text("🏷 Титул", {"cmd": "adm_title"}), color=KeyboardButtonColor.PRIMARY)
    kb.row()
    kb.add(Text("⚡ Энергия всем", {"cmd": "adm_energy_all"}), color=KeyboardButtonColor.POSITIVE)
    kb.add(Text("⏱ КД всем", {"cmd": "adm_cd_all"}), color=KeyboardButtonColor.PRIMARY)
    kb.row()
    kb.add(Text("💰 Топ богачей", {"cmd": "adm_top_rich"}), color=KeyboardButtonColor.SECONDARY)
    kb.add(Text("🔎 Поиск имени", {"cmd": "adm_find"}), color=KeyboardButtonColor.SECONDARY)
    kb.row()
    kb.add(Text("🎰 Джекпот", {"cmd": "adm_jackpot"}), color=KeyboardButtonColor.POSITIVE)
    kb.add(Text("🌧 Дождь стране", {"cmd": "adm_rain"}), color=KeyboardButtonColor.POSITIVE)
    kb.row()
    kb.add(Text("🎲 Лут/колесо", {"cmd": "adm_loot"}), color=KeyboardButtonColor.PRIMARY)
    kb.add(Text("📜 Хроника", {"cmd": "adm_chronicle"}), color=KeyboardButtonColor.SECONDARY)
    kb.row()
    kb.add(Text("📣 В беседы", {"cmd": "adm_bcast_chats"}), color=KeyboardButtonColor.PRIMARY)
    kb.add(Text("✉️ В ЛС", {"cmd": "adm_bcast_dms"}), color=KeyboardButtonColor.PRIMARY)
    kb.row()
    kb.add(Text("🗑 Удалить страну", {"cmd": "adm_del_nation"}), color=KeyboardButtonColor.NEGATIVE)
    kb.row()
    kb.add(Text("⏱ КД себе", {"cmd": "adm_cd_self"}), color=KeyboardButtonColor.PRIMARY)
    kb.add(Text("« Назад", {"cmd": "admin"}), color=KeyboardButtonColor.SECONDARY)
    return kb


def jobs_keyboard(level: int = 1) -> Keyboard:
    kb = Keyboard(one_time=False, inline=False)
    level = max(1, int(level or 1))

    def _job(label: str, job: str, color):
        req = config.JOB_LEVEL_REQ.get(job, 1)
        if level >= req:
            kb.add(Text(label, {"cmd": "job", "job": job}), color=color)
        else:
            kb.add(
                Text(f"🔒{req} {label}", {"cmd": "job_locked", "job": job, "req": req}),
                color=KeyboardButtonColor.SECONDARY,
            )

    _job("⛏ Шахта", "mine", KeyboardButtonColor.PRIMARY)
    _job("🛒 Рынок", "market", KeyboardButtonColor.POSITIVE)
    kb.row()
    _job("🎣 Рыбалка", "fish", KeyboardButtonColor.PRIMARY)
    _job("🌾 Поле", "farm", KeyboardButtonColor.POSITIVE)
    kb.row()
    _job("🔥 Кузня", "forge", KeyboardButtonColor.PRIMARY)
    _job("🍺 Таверна", "tavern", KeyboardButtonColor.POSITIVE)
    kb.row()
    _job("🐴 Конюшня", "stable", KeyboardButtonColor.PRIMARY)
    _job("🛡 Охрана", "guard", KeyboardButtonColor.NEGATIVE)
    kb.row()
    if level >= config.SMUGGLE_LEVEL_REQ:
        kb.add(Text("🕶 Контрабанда", {"cmd": "smuggle"}), color=KeyboardButtonColor.NEGATIVE)
    else:
        kb.add(
            Text(
                f"🔒{config.SMUGGLE_LEVEL_REQ} Контрабанда",
                {"cmd": "job_locked", "job": "smuggle"},
            ),
            color=KeyboardButtonColor.SECONDARY,
        )
    kb.row()
    kb.add(Text("📦 Привоз", {"cmd": "supply"}), color=KeyboardButtonColor.POSITIVE)
    kb.add(Text("📋 Заказы", {"cmd": "work_orders"}), color=KeyboardButtonColor.PRIMARY)
    kb.row()
    kb.add(Text("🗺 Путь", {"cmd": "work_path"}), color=KeyboardButtonColor.PRIMARY)
    kb.add(Text("🌟 Смена дня", {"cmd": "deep_work"}), color=KeyboardButtonColor.POSITIVE)
    kb.row()
    kb.add(Text("⭐ Уровни", {"cmd": "levels"}), color=KeyboardButtonColor.PRIMARY)
    kb.add(Text("🏪 Лавка", {"cmd": "shop"}), color=KeyboardButtonColor.SECONDARY)
    kb.row()
    kb.add(Text("📋 Меню", {"cmd": "menu"}), color=KeyboardButtonColor.SECONDARY)
    return kb


def supply_keyboard(stock: list) -> Keyboard:
    kb = Keyboard(one_time=False, inline=False)
    n = 0
    for s in stock or []:
        if int(s.get("qty") or 0) < 1:
            continue
        from content import items_catalog as cat

        it = cat.get_item(s["item_id"])
        label = (it["name"] if it else s["item_id"])[:18]
        kb.add(
            Text(f"{label} {s['price']}🪙", {"cmd": "supply_buy", "item": s["item_id"]}),
            color=KeyboardButtonColor.POSITIVE,
        )
        n += 1
        if n % 2 == 0:
            kb.row()
    if n % 2:
        kb.row()
    kb.add(Text("🔄 Обновить", {"cmd": "supply"}), color=KeyboardButtonColor.PRIMARY)
    kb.add(Text("« Работы", {"cmd": "jobs"}), color=KeyboardButtonColor.SECONDARY)
    kb.row()
    kb.add(Text("📋 Меню", {"cmd": "menu"}), color=KeyboardButtonColor.SECONDARY)
    return kb


def work_path_keyboard() -> Keyboard:
    kb = Keyboard(one_time=False, inline=False)
    kb.add(Text("🎣 Сети", {"cmd": "set_path", "path": "fish:net"}), color=KeyboardButtonColor.PRIMARY)
    kb.add(Text("🔱 Гарпун", {"cmd": "set_path", "path": "fish:spear"}), color=KeyboardButtonColor.PRIMARY)
    kb.row()
    kb.add(Text("⚔ Оружие", {"cmd": "set_path", "path": "forge:arms"}), color=KeyboardButtonColor.POSITIVE)
    kb.add(Text("🐴 Подковы", {"cmd": "set_path", "path": "forge:shoes"}), color=KeyboardButtonColor.POSITIVE)
    kb.row()
    kb.add(Text("« Работы", {"cmd": "jobs"}), color=KeyboardButtonColor.SECONDARY)
    return kb


def deep_job_keyboard(level: int = 1) -> Keyboard:
    """Выбор работы для смены дня."""
    kb = Keyboard(one_time=False, inline=False)
    level = max(1, int(level or 1))
    jobs = [
        ("⛏", "mine"),
        ("🛒", "market"),
        ("🎣", "fish"),
        ("🌾", "farm"),
        ("🔥", "forge"),
        ("🍺", "tavern"),
        ("🐴", "stable"),
        ("🛡", "guard"),
    ]
    n = 0
    for mark, job in jobs:
        req = config.JOB_LEVEL_REQ.get(job, 1)
        if level < req:
            continue
        title = config.JOBS[job]["title"]
        kb.add(
            Text(title, {"cmd": "deep_job", "job": job}),
            color=KeyboardButtonColor.POSITIVE,
        )
        n += 1
        if n % 2 == 0:
            kb.row()
    if n % 2:
        kb.row()
    kb.add(Text("« Работы", {"cmd": "jobs"}), color=KeyboardButtonColor.SECONDARY)
    return kb


def minigame_keyboard(token: str, buttons: list[tuple[str, str]]) -> Keyboard:
    kb = Keyboard(one_time=True, inline=False)
    for i, (label, answer) in enumerate(buttons):
        if i and i % 2 == 0:
            kb.row()
        kb.add(
            Text(label, {"cmd": "job_answer", "token": token, "answer": answer}),
            color=KeyboardButtonColor.PRIMARY,
        )
    return kb


def nation_keyboard(*, in_chat: bool, has_nation: bool, is_leader: bool) -> Keyboard:
    kb = Keyboard(one_time=False, inline=False)
    if has_nation:
        kb.add(Text("ℹ️ Инфо страны", {"cmd": "nation"}), color=KeyboardButtonColor.PRIMARY)
        kb.add(Text("🚪 Выйти", {"cmd": "leave_nation"}), color=KeyboardButtonColor.NEGATIVE)
        kb.row()
        kb.add(Text("🏛 Казна", {"cmd": "treasury"}), color=KeyboardButtonColor.PRIMARY)
        kb.add(Text("📅 Цель", {"cmd": "weekly"}), color=KeyboardButtonColor.POSITIVE)
        if is_leader:
            kb.row()
            kb.add(Text("🎨 Оформить", {"cmd": "customize"}), color=KeyboardButtonColor.POSITIVE)
            kb.add(Text("👑 Трон", {"cmd": "transfer_menu"}), color=KeyboardButtonColor.PRIMARY)
            kb.row()
            kb.add(Text("👑 Роли", {"cmd": "roles"}), color=KeyboardButtonColor.PRIMARY)
            kb.add(Text("🤝 Союз", {"cmd": "alliance"}), color=KeyboardButtonColor.POSITIVE)
            kb.row()
            kb.add(Text("🏙 Районы", {"cmd": "districts"}), color=KeyboardButtonColor.PRIMARY)
            kb.add(Text("⚔ Рейд", {"cmd": "war"}), color=KeyboardButtonColor.NEGATIVE)
            kb.row()
            kb.add(Text("🗑 Распустить", {"cmd": "dissolve_nation"}), color=KeyboardButtonColor.NEGATIVE)
        else:
            kb.row()
            kb.add(Text("🤝 Союз", {"cmd": "alliance"}), color=KeyboardButtonColor.POSITIVE)
            kb.add(Text("🏙 Районы", {"cmd": "districts"}), color=KeyboardButtonColor.PRIMARY)
            kb.row()
            kb.add(Text("⚔ Рейд", {"cmd": "war"}), color=KeyboardButtonColor.NEGATIVE)
            kb.add(Text("✋ В строй", {"cmd": "muster_join"}), color=KeyboardButtonColor.POSITIVE)
    else:
        if in_chat:
            kb.add(
                Text("🏗 Основать страну", {"cmd": "found_nation"}),
                color=KeyboardButtonColor.POSITIVE,
            )
            kb.add(Text("➕ Вступить", {"cmd": "join_nation"}), color=KeyboardButtonColor.PRIMARY)
        else:
            kb.add(
                Text("ℹ️ Нужна беседа", {"cmd": "need_chat"}),
                color=KeyboardButtonColor.SECONDARY,
            )
    kb.row()
    kb.add(Text("📋 Меню", {"cmd": "menu"}), color=KeyboardButtonColor.SECONDARY)
    return kb


def treasury_keyboard() -> Keyboard:
    kb = Keyboard(one_time=False, inline=False)
    kb.add(Text("⚒ Указ", {"cmd": "tr_spend", "action": "work"}), color=KeyboardButtonColor.POSITIVE)
    kb.add(Text("📜 Воен.сбор", {"cmd": "tr_spend", "action": "levy"}), color=KeyboardButtonColor.NEGATIVE)
    kb.row()
    kb.add(Text("💰 Раздача", {"cmd": "tr_spend", "action": "payout"}), color=KeyboardButtonColor.PRIMARY)
    kb.add(Text("🕊 Амнистия", {"cmd": "tr_spend", "action": "amnesty"}), color=KeyboardButtonColor.SECONDARY)
    kb.row()
    kb.add(Text("🎉 Праздник", {"cmd": "tr_spend", "action": "feast"}), color=KeyboardButtonColor.POSITIVE)
    kb.add(Text("🧱 Укрепление", {"cmd": "tr_spend", "action": "fortify"}), color=KeyboardButtonColor.PRIMARY)
    kb.row()
    kb.add(Text("📚 Стипендия", {"cmd": "tr_spend", "action": "scholar"}), color=KeyboardButtonColor.POSITIVE)
    kb.add(Text("⚔ Фонд рейда", {"cmd": "tr_spend", "action": "raid_fund"}), color=KeyboardButtonColor.NEGATIVE)
    kb.row()
    kb.add(Text("🛡 Казна→щит", {"cmd": "tr_spend", "action": "buy_shield"}), color=KeyboardButtonColor.PRIMARY)
    kb.add(Text("🗿 Монумент", {"cmd": "tr_spend", "action": "monument"}), color=KeyboardButtonColor.POSITIVE)
    kb.row()
    kb.add(Text("🛡 Взнос щит", {"cmd": "tr_spend", "action": "shield_pay"}), color=KeyboardButtonColor.SECONDARY)
    kb.add(Text("🛡 Активировать", {"cmd": "tr_spend", "action": "shield_on"}), color=KeyboardButtonColor.POSITIVE)
    kb.row()
    kb.add(Text("🏛 Страна", {"cmd": "nation"}), color=KeyboardButtonColor.SECONDARY)
    kb.add(Text("📋 Меню", {"cmd": "menu"}), color=KeyboardButtonColor.SECONDARY)
    return kb


def roles_keyboard() -> Keyboard:
    kb = Keyboard(one_time=False, inline=False)
    kb.add(Text("⚔ Воевода", {"cmd": "role_pick", "role": "warlord"}), color=KeyboardButtonColor.NEGATIVE)
    kb.add(Text("💰 Казначей", {"cmd": "role_pick", "role": "treasurer"}), color=KeyboardButtonColor.PRIMARY)
    kb.row()
    kb.add(Text("📢 Глашатай", {"cmd": "role_pick", "role": "herald"}), color=KeyboardButtonColor.POSITIVE)
    kb.row()
    kb.add(Text("❌ Снять воеводу", {"cmd": "role_pick", "role": "warlord", "clear": 1}))
    kb.add(Text("❌ Снять казначея", {"cmd": "role_pick", "role": "treasurer", "clear": 1}))
    kb.row()
    kb.add(Text("❌ Снять глашатая", {"cmd": "role_pick", "role": "herald", "clear": 1}))
    kb.add(Text("📋 Меню", {"cmd": "menu"}), color=KeyboardButtonColor.SECONDARY)
    return kb


def roles_assign_keyboard(role: str, citizens: list) -> Keyboard:
    kb = Keyboard(one_time=True, inline=False)
    for i, p in enumerate(citizens[:8]):
        if i and i % 2 == 0:
            kb.row()
        kb.add(
            Text(p.name[:18] or str(p.vk_id), {"cmd": "role_set", "role": role, "vk_id": p.vk_id}),
            color=KeyboardButtonColor.PRIMARY,
        )
    kb.row()
    kb.add(Text("👑 Роли", {"cmd": "roles"}), color=KeyboardButtonColor.SECONDARY)
    return kb


def customize_keyboard() -> Keyboard:
    kb = Keyboard(one_time=False, inline=False)
    kb.add(Text("🚩 Флаг", {"cmd": "c_flag"}), color=KeyboardButtonColor.PRIMARY)
    kb.add(Text("🛡️ Герб", {"cmd": "c_emblem"}), color=KeyboardButtonColor.PRIMARY)
    kb.row()
    kb.add(Text("💬 Девиз", {"cmd": "c_text", "field": "motto"}), color=KeyboardButtonColor.SECONDARY)
    kb.add(Text("🏙 Столица", {"cmd": "c_text", "field": "capital"}), color=KeyboardButtonColor.SECONDARY)
    kb.row()
    kb.add(Text("🎵 Гимн", {"cmd": "c_text", "field": "anthem"}), color=KeyboardButtonColor.SECONDARY)
    kb.add(Text("📜 Законы", {"cmd": "c_text", "field": "laws"}), color=KeyboardButtonColor.SECONDARY)
    kb.row()
    kb.add(Text("👋 Приветствие", {"cmd": "c_text", "field": "welcome"}), color=KeyboardButtonColor.SECONDARY)
    kb.add(Text("🏛 Строй", {"cmd": "c_gov"}), color=KeyboardButtonColor.PRIMARY)
    kb.row()
    kb.add(Text("🎨 Цвет", {"cmd": "c_color"}), color=KeyboardButtonColor.PRIMARY)
    kb.add(Text("💹 Налог", {"cmd": "c_tax"}), color=KeyboardButtonColor.POSITIVE)
    kb.row()
    kb.add(Text("🏛 Страна", {"cmd": "nation"}), color=KeyboardButtonColor.SECONDARY)
    return kb


def preset_keyboard(cmd: str, values: list[str], field: str | None = None) -> Keyboard:
    kb = Keyboard(one_time=True, inline=False)
    for i, val in enumerate(values):
        if i and i % 3 == 0:
            kb.row()
        payload = {"cmd": cmd, "value": val}
        if field:
            payload["field"] = field
        kb.add(Text(val, payload), color=KeyboardButtonColor.PRIMARY)
    kb.row()
    kb.add(Text("🎨 Оформить", {"cmd": "customize"}), color=KeyboardButtonColor.SECONDARY)
    return kb


def tax_keyboard() -> Keyboard:
    kb = Keyboard(one_time=True, inline=False)
    for rate in config.TAX_PRESETS:
        pct = int(rate * 100)
        kb.add(Text(f"{pct}%", {"cmd": "c_set", "field": "tax_rate", "value": str(rate)}))
    kb.row()
    kb.add(Text("🎨 Оформить", {"cmd": "customize"}), color=KeyboardButtonColor.SECONDARY)
    return kb


def citizens_keyboard(citizens: list) -> Keyboard:
    kb = Keyboard(one_time=True, inline=False)
    for i, p in enumerate(citizens):
        if i and i % 2 == 0:
            kb.row()
        kb.add(
            Text(p.name[:20] or str(p.vk_id), {"cmd": "transfer_to", "vk_id": p.vk_id}),
            color=KeyboardButtonColor.PRIMARY,
        )
    kb.row()
    kb.add(Text("🏛 Страна", {"cmd": "nation"}), color=KeyboardButtonColor.SECONDARY)
    return kb


def cancel_keyboard() -> Keyboard:
    kb = Keyboard(one_time=True, inline=False)
    kb.add(Text("❌ Отмена", {"cmd": "cancel"}), color=KeyboardButtonColor.NEGATIVE)
    return kb


def raid_targets_keyboard(names: list[str], *, cmd: str = "raid") -> Keyboard:
    kb = Keyboard(one_time=True, inline=False)
    emoji = "⚔" if cmd == "raid" else "🤝"
    color = (
        KeyboardButtonColor.NEGATIVE
        if cmd == "raid"
        else KeyboardButtonColor.POSITIVE
    )
    for i, name in enumerate(names[:6]):
        if i and i % 2 == 0:
            kb.row()
        kb.add(
            Text(f"{emoji} {name}", {"cmd": cmd, "target": name}),
            color=color,
        )
    kb.row()
    kb.add(Text("❌ Отмена", {"cmd": "alliance" if cmd != "raid" else "cancel"}), color=KeyboardButtonColor.SECONDARY)
    return kb


def districts_keyboard() -> Keyboard:
    kb = Keyboard(one_time=False, inline=False)
    kb.add(Text("🛒 Рынок", {"cmd": "district_up", "d": "market"}), color=KeyboardButtonColor.POSITIVE)
    kb.add(Text("⚔ Казарма", {"cmd": "district_up", "d": "barracks"}), color=KeyboardButtonColor.NEGATIVE)
    kb.row()
    kb.add(Text("🛕 Храм", {"cmd": "district_up", "d": "temple"}), color=KeyboardButtonColor.PRIMARY)
    kb.row()
    kb.add(Text("🏛 Страна", {"cmd": "nation"}), color=KeyboardButtonColor.SECONDARY)
    kb.add(Text("📋 Меню", {"cmd": "menu"}), color=KeyboardButtonColor.SECONDARY)
    return kb


def war_actions_keyboard(names: list[str]) -> Keyboard:
    kb = Keyboard(one_time=True, inline=False)
    kb.add(Text("📣 Сбор", {"cmd": "muster_open"}), color=KeyboardButtonColor.POSITIVE)
    kb.add(Text("✋ В строй", {"cmd": "muster_join"}), color=KeyboardButtonColor.PRIMARY)
    kb.row()
    kb.add(Text("🏰 Осада", {"cmd": "siege"}), color=KeyboardButtonColor.NEGATIVE)
    kb.row()
    for i, name in enumerate(names[:6]):
        if i and i % 2 == 0:
            kb.row()
        kb.add(Text(f"⚔ {name}", {"cmd": "raid", "target": name}), color=KeyboardButtonColor.NEGATIVE)
    kb.row()
    kb.add(Text("❌ Отмена", {"cmd": "cancel"}), color=KeyboardButtonColor.SECONDARY)
    return kb


def alliance_keyboard(*, is_leader: bool) -> Keyboard:
    kb = Keyboard(one_time=False, inline=False)
    if is_leader:
        kb.add(Text("📨 Предложить", {"cmd": "ally_propose"}), color=KeyboardButtonColor.POSITIVE)
        kb.add(Text("✅ Принять", {"cmd": "ally_accept"}), color=KeyboardButtonColor.PRIMARY)
        kb.row()
        kb.add(Text("❌ Отклонить", {"cmd": "ally_reject"}), color=KeyboardButtonColor.SECONDARY)
        kb.add(Text("💔 Разорвать", {"cmd": "ally_break"}), color=KeyboardButtonColor.NEGATIVE)
        kb.row()
    kb.add(Text("🏛 Страна", {"cmd": "nation"}), color=KeyboardButtonColor.SECONDARY)
    kb.add(Text("📋 Меню", {"cmd": "menu"}), color=KeyboardButtonColor.SECONDARY)
    return kb


def confirm_dissolve_keyboard() -> Keyboard:
    kb = Keyboard(one_time=True, inline=False)
    kb.add(
        Text("Да, распустить", {"cmd": "dissolve_confirm"}),
        color=KeyboardButtonColor.NEGATIVE,
    )
    kb.add(Text("❌ Отмена", {"cmd": "nation"}), color=KeyboardButtonColor.SECONDARY)
    return kb


def bag_keyboard(page: int = 0, has_next: bool = False) -> Keyboard:
    kb = Keyboard(one_time=False, inline=False)
    kb.add(Text("🛡 Экипировка", {"cmd": "bag_eq"}), color=KeyboardButtonColor.PRIMARY)
    kb.add(Text("📖 Кодекс", {"cmd": "codex"}), color=KeyboardButtonColor.SECONDARY)
    kb.row()
    if page > 0:
        kb.add(Text("⬅", {"cmd": "bag", "page": page - 1}))
    if has_next:
        kb.add(Text("➡", {"cmd": "bag", "page": page + 1}))
    kb.row()
    kb.add(Text("⚡ Заряды", {"cmd": "bag_charges"}), color=KeyboardButtonColor.POSITIVE)
    kb.add(Text("🛒 Торг", {"cmd": "market_menu"}), color=KeyboardButtonColor.POSITIVE)
    kb.row()
    kb.add(
        Text("🧹 Слить хлам", {"cmd": "bag_junk"}),
        color=KeyboardButtonColor.PRIMARY,
    )
    kb.add(Text("📋 Меню", {"cmd": "menu"}), color=KeyboardButtonColor.SECONDARY)
    return kb


def bag_items_keyboard(items: list[tuple], page: int, has_next: bool = False) -> Keyboard:
    """items: list of (item_dict, qty) for current page."""
    kb = Keyboard(one_time=True, inline=False)
    for i, (it, qty) in enumerate(items):
        if i and i % 2 == 0:
            kb.row()
        label = f"{it['name'][:14]}×{qty}"
        kb.add(Text(label, {"cmd": "bag_item", "id": it["id"]}), color=KeyboardButtonColor.PRIMARY)
    kb.row()
    if page > 0:
        kb.add(Text("⬅", {"cmd": "bag", "page": page - 1}))
    if has_next:
        kb.add(Text("➡", {"cmd": "bag", "page": page + 1}))
    kb.row()
    kb.add(Text("🛡 Экип", {"cmd": "bag_eq"}), color=KeyboardButtonColor.PRIMARY)
    kb.add(Text("📖 Кодекс", {"cmd": "codex"}), color=KeyboardButtonColor.SECONDARY)
    kb.row()
    kb.add(Text("⚡ Заряды", {"cmd": "bag_charges"}), color=KeyboardButtonColor.POSITIVE)
    kb.add(Text("🛒 Торг", {"cmd": "market_menu"}), color=KeyboardButtonColor.POSITIVE)
    kb.row()
    kb.add(
        Text("🧹 Слить хлам", {"cmd": "bag_junk"}),
        color=KeyboardButtonColor.PRIMARY,
    )
    kb.add(Text("📋 Меню", {"cmd": "menu"}), color=KeyboardButtonColor.SECONDARY)
    return kb


def item_actions_keyboard(item_id: str, rarity: str) -> Keyboard:
    kb = Keyboard(one_time=True, inline=False)
    kb.add(Text("✅ Экип", {"cmd": "bag_equip", "id": item_id}), color=KeyboardButtonColor.POSITIVE)
    kb.add(Text("⚒ Заточить", {"cmd": "bag_upgrade", "id": item_id}), color=KeyboardButtonColor.PRIMARY)
    kb.row()
    kb.add(Text("🛒 На торг", {"cmd": "mkt_sell_menu", "id": item_id}), color=KeyboardButtonColor.POSITIVE)
    kb.add(Text("💰 Продать боту", {"cmd": "bag_sell", "id": item_id}), color=KeyboardButtonColor.PRIMARY)
    kb.row()
    if rarity == "common":
        kb.add(Text("🔀 Слить×3", {"cmd": "bag_merge", "id": item_id}), color=KeyboardButtonColor.SECONDARY)
    if rarity in ("epic", "legendary", "mythic"):
        kb.add(Text("🏛 В казну", {"cmd": "bag_donate", "id": item_id}), color=KeyboardButtonColor.PRIMARY)
    kb.row()
    kb.add(Text("🎒 Сумка", {"cmd": "bag"}), color=KeyboardButtonColor.SECONDARY)
    return kb


def confirm_sell_bot_keyboard(item_id: str, price_one: int, qty_all: int, price_all: int) -> Keyboard:
    kb = Keyboard(one_time=True, inline=False)
    kb.add(
        Text(
            f"×1 за {price_one}",
            {"cmd": "bag_sell_confirm", "id": item_id, "qty": 1},
        ),
        color=KeyboardButtonColor.POSITIVE,
    )
    if qty_all > 1:
        kb.add(
            Text(
                f"Все ×{qty_all} за {price_all}",
                {"cmd": "bag_sell_confirm", "id": item_id, "qty": qty_all},
            ),
            color=KeyboardButtonColor.PRIMARY,
        )
    kb.row()
    kb.add(
        Text("❌ Отмена", {"cmd": "bag_item", "id": item_id}),
        color=KeyboardButtonColor.NEGATIVE,
    )
    return kb


def confirm_junk_sell_keyboard(price: int, qty: int) -> Keyboard:
    kb = Keyboard(one_time=True, inline=False)
    kb.add(
        Text(
            f"Слить {qty} шт. за {price}",
            {"cmd": "bag_junk_confirm"},
        ),
        color=KeyboardButtonColor.POSITIVE,
    )
    kb.add(Text("❌ Отмена", {"cmd": "bag"}), color=KeyboardButtonColor.NEGATIVE)
    return kb


def market_menu_keyboard() -> Keyboard:
    kb = Keyboard(one_time=False, inline=False)
    kb.add(Text("🛒 Витрина", {"cmd": "market", "page": 0}), color=KeyboardButtonColor.POSITIVE)
    kb.add(Text("🔎 Поиск", {"cmd": "mkt_help"}), color=KeyboardButtonColor.PRIMARY)
    kb.row()
    kb.add(Text("⬜ Обычн.", {"cmd": "market", "rarity": "common", "page": 0}))
    kb.add(Text("🟩 Необыч.", {"cmd": "market", "rarity": "uncommon", "page": 0}))
    kb.add(Text("🟦 Редк.", {"cmd": "market", "rarity": "rare", "page": 0}))
    kb.row()
    kb.add(Text("🟪 Эпик", {"cmd": "market", "rarity": "epic", "page": 0}))
    kb.add(Text("🟨 Легенд.", {"cmd": "market", "rarity": "legendary", "page": 0}))
    kb.add(Text("🟥 Миф", {"cmd": "market", "rarity": "mythic", "page": 0}))
    kb.row()
    kb.add(Text("📦 Мои лоты", {"cmd": "mkt_mine"}), color=KeyboardButtonColor.SECONDARY)
    kb.add(Text("🎯 Ещё", {"cmd": "more"}), color=KeyboardButtonColor.SECONDARY)
    return kb


def market_listings_keyboard(
    listings: list,
    *,
    page: int = 0,
    rarity: str | None = None,
    query: str | None = None,
    has_next: bool = False,
    mine: bool = False,
) -> Keyboard:
    kb = Keyboard(one_time=True, inline=False)
    for i, listing in enumerate(listings[:6]):
        if i and i % 2 == 0:
            kb.row()
        from content import items_catalog as cat

        it = cat.get_item(listing.item_id)
        name = (it["name"] if it else listing.item_id)[:12]
        kb.add(
            Text(
                f"#{listing.id} {name} {listing.price}",
                {"cmd": "mkt_view", "id": listing.id},
            ),
            color=KeyboardButtonColor.PRIMARY,
        )
    kb.row()
    nav_payload = {"cmd": "market", "page": page}
    if rarity:
        nav_payload["rarity"] = rarity
    if query:
        nav_payload["q"] = query
    if mine:
        nav_payload = {"cmd": "mkt_mine", "page": page}
    if page > 0:
        prev = dict(nav_payload)
        prev["page"] = page - 1
        kb.add(Text("⬅", prev))
    if has_next:
        nxt = dict(nav_payload)
        nxt["page"] = page + 1
        kb.add(Text("➡", nxt))
    kb.row()
    kb.add(Text("🛒 Торг", {"cmd": "market_menu"}), color=KeyboardButtonColor.SECONDARY)
    return kb


def market_listing_actions_keyboard(listing_id: int, *, is_owner: bool) -> Keyboard:
    kb = Keyboard(one_time=True, inline=False)
    if is_owner:
        kb.add(
            Text("❌ Снять лот", {"cmd": "mkt_cancel", "id": listing_id}),
            color=KeyboardButtonColor.NEGATIVE,
        )
    else:
        kb.add(
            Text("✅ Купить", {"cmd": "mkt_buy", "id": listing_id}),
            color=KeyboardButtonColor.POSITIVE,
        )
    kb.row()
    kb.add(Text("🛒 Торг", {"cmd": "market_menu"}), color=KeyboardButtonColor.SECONDARY)
    return kb


def market_price_keyboard(item_id: str) -> Keyboard:
    kb = Keyboard(one_time=True, inline=False)
    prices = (50, 100, 200, 500, 1000, 2500, 5000, 10000)
    for i, price in enumerate(prices):
        if i and i % 4 == 0:
            kb.row()
        kb.add(
            Text(str(price), {"cmd": "mkt_list", "id": item_id, "price": price}),
            color=KeyboardButtonColor.POSITIVE,
        )
    kb.row()
    kb.add(Text("❌ Отмена", {"cmd": "market_menu"}), color=KeyboardButtonColor.NEGATIVE)
    kb.add(Text("🎒 Сумка", {"cmd": "bag"}), color=KeyboardButtonColor.SECONDARY)
    return kb


def unequip_keyboard() -> Keyboard:
    kb = Keyboard(one_time=True, inline=False)
    for slot, label in [("tool", "Инструмент"), ("weapon", "Оружие"), ("relic", "Реликвия")]:
        kb.add(Text(f"Снять {label}", {"cmd": "bag_unequip", "slot": slot}))
    kb.row()
    kb.add(Text("🎒 Сумка", {"cmd": "bag"}), color=KeyboardButtonColor.SECONDARY)
    return kb


def charge_activate_keyboard(codes: list[str]) -> Keyboard:
    from services.charges import MANUAL_CHARGES

    kb = Keyboard(one_time=True, inline=False)
    for code in codes:
        if code == "tax_override_week":
            continue
        label = MANUAL_CHARGES.get(code, code)[:36]
        kb.add(Text(label, {"cmd": "bag_charge", "code": code}), color=KeyboardButtonColor.POSITIVE)
        kb.row()
    if "tax_override_week" in codes:
        for rate in config.TAX_PRESETS:
            kb.add(
                Text(
                    f"Налог {int(rate * 100)}%",
                    {
                        "cmd": "bag_charge",
                        "code": "tax_override_week",
                        "tax": str(rate),
                    },
                )
            )
        kb.row()
    kb.add(Text("🎒 Сумка", {"cmd": "bag"}), color=KeyboardButtonColor.SECONDARY)
    return kb
