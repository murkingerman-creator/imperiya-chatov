from vkbottle.bot import Bot, Message

from bot import config
from bot.keyboards import customize_keyboard, main_keyboard, preset_keyboard, tax_keyboard, cancel_keyboard
from db.database import SessionLocal
from handlers.common import resolve_name
from handlers.nation import get_pending_text
from handlers.rules import match_cmd, payload_cmd
from services.customize import CustomizeError, set_field
from services.player import get_or_create_player


def register(bot: Bot) -> None:
    @bot.on.message(func=match_cmd("customize", "🎨 оформить", "оформить"))
    async def customize_menu(message: Message):
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            if not player.nation or player.nation.leader_id != player.vk_id:
                await message.answer(
                    "Оформление доступно только лидеру страны.",
                    keyboard=main_keyboard().get_json(),
                )
                return
            await message.answer(
                "🎨 Оформление державы\n"
                f"Частая смена (<{config.CUSTOMIZE_COOLDOWN_HOURS}ч) стоит "
                f"{config.CUSTOMIZE_CHANGE_COST} крон.",
                keyboard=customize_keyboard().get_json(),
            )

    @bot.on.message(func=payload_cmd("c_flag"))
    async def pick_flag(message: Message):
        await message.answer(
            "Выбери флаг:",
            keyboard=preset_keyboard("c_set", list(config.FLAGS), field="flag_emoji").get_json(),
        )

    @bot.on.message(func=payload_cmd("c_emblem"))
    async def pick_emblem(message: Message):
        await message.answer(
            "Выбери герб:",
            keyboard=preset_keyboard("c_set", list(config.EMBLEMS), field="emblem_emoji").get_json(),
        )

    @bot.on.message(func=payload_cmd("c_gov"))
    async def pick_gov(message: Message):
        await message.answer(
            "Форма правления:",
            keyboard=preset_keyboard("c_set", list(config.GOVERNMENTS), field="government").get_json(),
        )

    @bot.on.message(func=payload_cmd("c_color"))
    async def pick_color(message: Message):
        await message.answer(
            "Цвет державы:",
            keyboard=preset_keyboard("c_set", list(config.COLORS), field="color_tag").get_json(),
        )

    @bot.on.message(func=payload_cmd("c_tax"))
    async def pick_tax(message: Message):
        await message.answer("Налог с работы граждан:", keyboard=tax_keyboard().get_json())

    @bot.on.message(func=payload_cmd("c_text"))
    async def ask_text(message: Message):
        payload = message.get_payload_json() or {}
        field = str(payload.get("field") or "")
        labels = {
            "motto": "девиз",
            "capital": "столицу",
            "anthem": "гимн",
            "laws": "законы",
            "welcome": "приветствие",
        }
        if field not in labels:
            return
        get_pending_text()[(message.peer_id, message.from_id)] = field
        await message.answer(
            f"Введи {labels[field]} текстом:",
            keyboard=cancel_keyboard().get_json(),
        )

    @bot.on.message(func=payload_cmd("c_set"))
    async def apply_preset(message: Message):
        payload = message.get_payload_json() or {}
        field = str(payload.get("field") or "")
        value = str(payload.get("value") or "")
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            try:
                result = await set_field(session, player, field, value)
            except CustomizeError as e:
                await message.answer(e.message, keyboard=customize_keyboard().get_json())
                return
            cost_line = f" (−{result['cost']} крон)" if result["cost"] else ""
            await message.answer(
                f"Готово: {field} = {value}{cost_line}",
                keyboard=customize_keyboard().get_json(),
            )
