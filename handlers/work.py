from vkbottle.bot import Bot, Message

from bot.keyboards import main_keyboard
from db.database import SessionLocal
from handlers.common import resolve_name
from handlers.rules import match_cmd
from services.economy import WorkError, do_work
from services.player import get_or_create_player


def register(bot: Bot) -> None:
    @bot.on.message(func=match_cmd("work", "работа", "💼 работа", "работать"))
    async def work_handler(message: Message):
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            try:
                result = await do_work(session, player)
            except WorkError as e:
                await message.answer(e.message, keyboard=main_keyboard().get_json())
                return

            tax_line = ""
            if result["tax"]:
                tax_line = (
                    f"\n🏛 Налог в казну «{result['nation_name']}»: −{result['tax']}"
                )

            text = (
                f"💼 Смена закрыта!\n"
                f"Заработано: +{result['gross']} крон{tax_line}\n"
                f"На руки: +{result['net']}\n"
                f"💰 Баланс: {result['crowns']}\n"
                f"⚡ Энергия: {result['energy']}"
            )
            await message.answer(text, keyboard=main_keyboard().get_json())
