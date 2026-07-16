from vkbottle import Keyboard, KeyboardButtonColor, Text

from bot import config


def main_keyboard() -> Keyboard:
    kb = Keyboard(one_time=False, inline=False)
    kb.add(Text("👤 Профиль", {"cmd": "profile"}), color=KeyboardButtonColor.PRIMARY)
    kb.add(Text("🎁 Ежедневка", {"cmd": "daily"}), color=KeyboardButtonColor.POSITIVE)
    kb.row()
    kb.add(Text("💼 Работа", {"cmd": "jobs"}), color=KeyboardButtonColor.POSITIVE)
    kb.add(Text("🏛 Страна", {"cmd": "nation"}), color=KeyboardButtonColor.PRIMARY)
    kb.row()
    kb.add(Text("⚔ Война", {"cmd": "war"}), color=KeyboardButtonColor.NEGATIVE)
    kb.add(Text("📨 Инвайт", {"cmd": "invite"}), color=KeyboardButtonColor.SECONDARY)
    kb.row()
    kb.add(Text("🏆 Топ стран", {"cmd": "top_nations"}), color=KeyboardButtonColor.SECONDARY)
    kb.add(Text("💰 Топ игроков", {"cmd": "top_players"}), color=KeyboardButtonColor.SECONDARY)
    kb.row()
    kb.add(Text("📋 Меню", {"cmd": "menu"}), color=KeyboardButtonColor.SECONDARY)
    return kb


def jobs_keyboard() -> Keyboard:
    kb = Keyboard(one_time=False, inline=False)
    kb.add(Text("⛏ Шахта", {"cmd": "job", "job": "mine"}), color=KeyboardButtonColor.PRIMARY)
    kb.add(Text("🛒 Рынок", {"cmd": "job", "job": "market"}), color=KeyboardButtonColor.POSITIVE)
    kb.row()
    kb.add(Text("🛡 Охрана", {"cmd": "job", "job": "guard"}), color=KeyboardButtonColor.NEGATIVE)
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
        if is_leader:
            kb.row()
            kb.add(Text("🎨 Оформить", {"cmd": "customize"}), color=KeyboardButtonColor.POSITIVE)
            kb.add(Text("👑 Трон", {"cmd": "transfer_menu"}), color=KeyboardButtonColor.PRIMARY)
            kb.row()
            kb.add(Text("⚔ Рейд", {"cmd": "war"}), color=KeyboardButtonColor.NEGATIVE)
            kb.add(Text("🗑 Распустить", {"cmd": "dissolve_nation"}), color=KeyboardButtonColor.NEGATIVE)
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
