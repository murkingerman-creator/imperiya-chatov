from vkbottle import Keyboard, KeyboardButtonColor, Text


def main_keyboard() -> Keyboard:
    kb = Keyboard(one_time=False, inline=False)
    kb.add(Text("👤 Профиль", {"cmd": "profile"}), color=KeyboardButtonColor.PRIMARY)
    kb.add(Text("💼 Работа", {"cmd": "work"}), color=KeyboardButtonColor.POSITIVE)
    kb.row()
    kb.add(Text("🏛 Страна", {"cmd": "nation"}), color=KeyboardButtonColor.PRIMARY)
    kb.add(Text("⚔ Война", {"cmd": "war"}), color=KeyboardButtonColor.NEGATIVE)
    kb.row()
    kb.add(Text("🏆 Топ стран", {"cmd": "top_nations"}), color=KeyboardButtonColor.SECONDARY)
    kb.add(Text("💰 Топ игроков", {"cmd": "top_players"}), color=KeyboardButtonColor.SECONDARY)
    kb.row()
    kb.add(Text("📋 Меню", {"cmd": "menu"}), color=KeyboardButtonColor.SECONDARY)
    return kb


def nation_keyboard(*, in_chat: bool, has_nation: bool, is_leader: bool) -> Keyboard:
    kb = Keyboard(one_time=False, inline=False)
    if has_nation:
        kb.add(Text("ℹ️ Инфо страны", {"cmd": "nation"}), color=KeyboardButtonColor.PRIMARY)
        if is_leader:
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
