from vkbottle import Keyboard, KeyboardButtonColor, Text


def main_keyboard() -> Keyboard:
    kb = Keyboard(one_time=False, inline=False)
    kb.add(Text("👤 Профиль"), color=KeyboardButtonColor.PRIMARY)
    kb.add(Text("💼 Работа"), color=KeyboardButtonColor.POSITIVE)
    kb.row()
    kb.add(Text("🏛 Страна"), color=KeyboardButtonColor.PRIMARY)
    kb.add(Text("⚔ Война"), color=KeyboardButtonColor.NEGATIVE)
    kb.row()
    kb.add(Text("🏆 Топ стран"), color=KeyboardButtonColor.SECONDARY)
    kb.add(Text("💰 Топ игроков"), color=KeyboardButtonColor.SECONDARY)
    kb.row()
    kb.add(Text("📋 Меню"), color=KeyboardButtonColor.SECONDARY)
    return kb


def nation_keyboard(*, in_chat: bool, has_nation: bool, is_leader: bool) -> Keyboard:
    kb = Keyboard(one_time=False, inline=False)
    if has_nation:
        kb.add(Text("ℹ️ Инфо страны"), color=KeyboardButtonColor.PRIMARY)
        if is_leader and in_chat:
            kb.row()
            kb.add(Text("⚔ Рейд"), color=KeyboardButtonColor.NEGATIVE)
    else:
        if in_chat:
            kb.add(Text("🏗 Основать страну"), color=KeyboardButtonColor.POSITIVE)
            kb.add(Text("➕ Вступить"), color=KeyboardButtonColor.PRIMARY)
        else:
            kb.add(Text("ℹ️ Нужна беседа"), color=KeyboardButtonColor.SECONDARY)
    kb.row()
    kb.add(Text("📋 Меню"), color=KeyboardButtonColor.SECONDARY)
    return kb


def cancel_keyboard() -> Keyboard:
    kb = Keyboard(one_time=True, inline=False)
    kb.add(Text("❌ Отмена"), color=KeyboardButtonColor.NEGATIVE)
    return kb


def raid_targets_keyboard(names: list[str]) -> Keyboard:
    kb = Keyboard(one_time=True, inline=False)
    for i, name in enumerate(names[:6]):
        if i and i % 2 == 0:
            kb.row()
        kb.add(Text(f"⚔ {name}"), color=KeyboardButtonColor.NEGATIVE)
    kb.row()
    kb.add(Text("❌ Отмена"), color=KeyboardButtonColor.SECONDARY)
    return kb
