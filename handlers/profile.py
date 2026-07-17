from vkbottle.bot import Bot, Message

from bot import config
from bot.keyboards import main_keyboard
from db.database import SessionLocal
from handlers.common import reply, resolve_name
from handlers.rules import match_cmd
from services.achievements import format_titles
from services.inventory import discovered_count, get_equipped
from services.player import (
    energy_next_in_minutes,
    ensure_aware,
    get_or_create_player,
    regenerate_energy,
    utcnow,
)
from services.world_events import format_event, get_active_event
from content import items_catalog as cat


def register(bot: Bot) -> None:
    @bot.on.message(func=match_cmd("profile", "профиль", "👤 профиль", "я"))
    async def profile_handler(message: Message):
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            regenerate_energy(player)
            await session.commit()
            ev = await get_active_event(session)
            equipped = await get_equipped(session, player.vk_id)
            codex_n = await discovered_count(session, player.vk_id)

            nation_line = "не в стране"
            if player.nation:
                nation_line = f"{player.nation.flag_emoji} {player.nation.name}"
                if player.nation.leader_id == player.vk_id:
                    nation_line += " (лидер)"

            next_e = energy_next_in_minutes(player)
            energy_hint = (
                "полная"
                if next_e is None
                else f"+1 через ~{next_e} мин"
            )

            jail_line = ""
            until = ensure_aware(player.jail_until)
            if until and utcnow() < until:
                left = int((until - utcnow()).total_seconds() / 60) + 1
                jail_line = f"\n🚔 Тюрьма: ещё ~{left} мин"

            eq_line = (
                ", ".join(cat.format_item(it) for it in equipped.values())
                if equipped
                else "пусто"
            )

            text = (
                f"👤 {player.name}\n"
                f"💰 Кроны: {player.crowns}\n"
                f"⚡ Энергия: {player.energy}/{config.MAX_ENERGY} ({energy_hint})\n"
                f"🔥 Стрик ежедневки: {player.daily_streak or 0}\n"
                f"🏅 Титулы: {format_titles(player)}\n"
                f"🎒 Экип: {eq_line}\n"
                f"📖 Кодекс: {codex_n}/{cat.catalog_size()}\n"
                f"📨 Код: {player.invite_code}\n"
                f"🏛 Страна: {nation_line}"
                f"{jail_line}\n"
                f"{format_event(ev)}"
            )
            await reply(message, text, keyboard=main_keyboard().get_json())
