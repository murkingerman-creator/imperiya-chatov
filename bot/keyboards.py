from vkbottle import Keyboard, KeyboardButtonColor, Text

from bot import config


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
    kb.add(Text("💡 Предложение", {"cmd": "suggest"}), color=KeyboardButtonColor.POSITIVE)
    kb.add(Text("📖 Как играть", {"cmd": "guide"}), color=KeyboardButtonColor.PRIMARY)
    kb.row()
    kb.add(Text("📋 Меню", {"cmd": "menu"}), color=KeyboardButtonColor.SECONDARY)
    return kb


def shop_keyboard(*, jailed: bool = False) -> Keyboard:
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
    kb.add(
        Text("🏛 В казну", {"cmd": "shop_buy", "item": "treasury"}),
        color=KeyboardButtonColor.PRIMARY,
    )
    kb.add(
        Text("⚔ Знамя", {"cmd": "shop_buy", "item": "raid_bless"}),
        color=KeyboardButtonColor.NEGATIVE,
    )
    kb.row()
    kb.add(
        Text("🎰 Колесо", {"cmd": "shop_buy", "item": "wheel"}),
        color=KeyboardButtonColor.POSITIVE,
    )
    kb.add(
        Text("🛡 Щит", {"cmd": "tr_spend", "action": "shield_pay"}),
        color=KeyboardButtonColor.PRIMARY,
    )
    kb.row()
    if not jailed:
        kb.add(
            Text("🔓 Выкуп", {"cmd": "shop_buy", "item": "bail"}),
            color=KeyboardButtonColor.SECONDARY,
        )
    kb.add(Text("📋 Меню", {"cmd": "menu"}), color=KeyboardButtonColor.SECONDARY)
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


def duel_accept_keyboard(token: str) -> Keyboard:
    # inline — в беседе не подменяет общую reply-клавиатуру
    kb = Keyboard(one_time=True, inline=True)
    kb.add(
        Text("✅ Принять дуэль", {"cmd": "duel_accept", "token": token}),
        color=KeyboardButtonColor.POSITIVE,
    )
    return kb


def rps_keyboard(token: str) -> Keyboard:
    kb = Keyboard(one_time=True, inline=True)
    for label, move in [("✊ Камень", "rock"), ("✋ Бумага", "paper"), ("✌ Ножницы", "scissors")]:
        kb.add(Text(label, {"cmd": "duel_move", "token": token, "move": move}))
    return kb


def number_keyboard(token: str) -> Keyboard:
    kb = Keyboard(one_time=True, inline=True)
    for n in range(1, 6):
        kb.add(Text(str(n), {"cmd": "duel_move", "token": token, "move": str(n)}))
        if n == 3:
            kb.row()
    return kb


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
    kb.add(Text("⏱ Сброс КД себе", {"cmd": "adm_cd_self"}), color=KeyboardButtonColor.PRIMARY)
    kb.add(Text("⏱ Сброс КД игроку", {"cmd": "adm_cd"}), color=KeyboardButtonColor.PRIMARY)
    kb.row()
    kb.add(Text("🔎 Игрок", {"cmd": "adm_player"}), color=KeyboardButtonColor.SECONDARY)
    kb.add(Text("🗑 Удалить страну", {"cmd": "adm_del_nation"}), color=KeyboardButtonColor.NEGATIVE)
    kb.row()
    kb.add(Text("📜 Пост хроники", {"cmd": "adm_chronicle"}), color=KeyboardButtonColor.SECONDARY)
    kb.row()
    kb.add(Text("📣 В беседы", {"cmd": "adm_bcast_chats"}), color=KeyboardButtonColor.PRIMARY)
    kb.add(Text("✉️ В ЛС", {"cmd": "adm_bcast_dms"}), color=KeyboardButtonColor.PRIMARY)
    kb.row()
    kb.add(Text("📣✉️ Везде", {"cmd": "adm_bcast_all"}), color=KeyboardButtonColor.POSITIVE)
    kb.row()
    kb.add(Text("💡 Предложения", {"cmd": "adm_suggestions"}), color=KeyboardButtonColor.PRIMARY)
    kb.add(Text("📋 Меню", {"cmd": "menu"}), color=KeyboardButtonColor.SECONDARY)
    return kb


def jobs_keyboard() -> Keyboard:
    kb = Keyboard(one_time=False, inline=False)
    kb.add(Text("⛏ Шахта", {"cmd": "job", "job": "mine"}), color=KeyboardButtonColor.PRIMARY)
    kb.add(Text("🛒 Рынок", {"cmd": "job", "job": "market"}), color=KeyboardButtonColor.POSITIVE)
    kb.row()
    kb.add(Text("🎣 Рыбалка", {"cmd": "job", "job": "fish"}), color=KeyboardButtonColor.PRIMARY)
    kb.add(Text("🌾 Поле", {"cmd": "job", "job": "farm"}), color=KeyboardButtonColor.POSITIVE)
    kb.row()
    kb.add(Text("🔥 Кузня", {"cmd": "job", "job": "forge"}), color=KeyboardButtonColor.PRIMARY)
    kb.add(Text("🍺 Таверна", {"cmd": "job", "job": "tavern"}), color=KeyboardButtonColor.POSITIVE)
    kb.row()
    kb.add(Text("🛡 Охрана", {"cmd": "job", "job": "guard"}), color=KeyboardButtonColor.NEGATIVE)
    kb.add(Text("🕶 Контрабанда", {"cmd": "smuggle"}), color=KeyboardButtonColor.NEGATIVE)
    kb.row()
    kb.add(Text("🔓 Выкуп", {"cmd": "shop_buy", "item": "bail"}), color=KeyboardButtonColor.POSITIVE)
    kb.add(Text("🏪 Лавка", {"cmd": "shop"}), color=KeyboardButtonColor.SECONDARY)
    kb.row()
    kb.add(Text("📋 Меню", {"cmd": "menu"}), color=KeyboardButtonColor.SECONDARY)
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
            kb.add(Text("⚔ Рейд", {"cmd": "war"}), color=KeyboardButtonColor.NEGATIVE)
            kb.row()
            kb.add(Text("🗑 Распустить", {"cmd": "dissolve_nation"}), color=KeyboardButtonColor.NEGATIVE)
        else:
            kb.row()
            kb.add(Text("⚔ Рейд", {"cmd": "war"}), color=KeyboardButtonColor.NEGATIVE)
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
    kb.add(Text("🛡 Взнос щит", {"cmd": "tr_spend", "action": "shield_pay"}), color=KeyboardButtonColor.PRIMARY)
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


def raid_targets_keyboard(names: list[str]) -> Keyboard:
    kb = Keyboard(one_time=True, inline=False)
    for i, name in enumerate(names[:6]):
        if i and i % 2 == 0:
            kb.row()
        kb.add(Text(f"⚔ {name}", {"cmd": "raid", "target": name}), color=KeyboardButtonColor.NEGATIVE)
    kb.row()
    kb.add(Text("❌ Отмена", {"cmd": "cancel"}), color=KeyboardButtonColor.SECONDARY)
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


def confirm_sell_bot_keyboard(item_id: str, price: int) -> Keyboard:
    kb = Keyboard(one_time=True, inline=False)
    kb.add(
        Text(
            f"Да, продать за {price}",
            {"cmd": "bag_sell_confirm", "id": item_id},
        ),
        color=KeyboardButtonColor.POSITIVE,
    )
    kb.add(
        Text("❌ Отмена", {"cmd": "bag_item", "id": item_id}),
        color=KeyboardButtonColor.NEGATIVE,
    )
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
