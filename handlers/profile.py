from vkbottle.bot import Bot, Message

from bot import config
from bot.keyboards import main_keyboard
from db.database import SessionLocal
from handlers.common import reply, resolve_name
from handlers.rules import match_cmd
from services.achievements import format_titles
from services.cataclysm import format_cataclysm, get_cataclysm
from services.empire import format_empire_line, get_empire_status
from services.inventory import discovered_count, get_equipped
from services.levels import format_level_line, sync_level
from services.professions import format_professions_line
from services.tax_week import tax_paid_display
from services.player import (
    energy_next_in_minutes,
    ensure_aware,
    get_or_create_player,
    regenerate_energy,
    utcnow,
)
from services.flash_events import format_flash_event, get_flash_event
from services.world_events import format_event, get_active_event
from content import items_catalog as cat


def _bar(label: str, cur: int, goal: int) -> str:
    cur = max(0, int(cur))
    goal = max(1, int(goal))
    filled = min(10, int(round(10 * min(cur, goal) / goal)))
    return f"{label}: [{'█' * filled}{'░' * (10 - filled)}] {min(cur, goal)}/{goal}"


def register(bot: Bot) -> None:
    @bot.on.message(func=match_cmd("profile", "профиль", "👤 профиль", "я"))
    async def profile_handler(message: Message):
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            regenerate_energy(player)
            sync_level(player)
            await session.commit()
            ev = await get_active_event(session)
            flash = await get_flash_event(session)
            equipped = await get_equipped(session, player.vk_id)
            codex_n = await discovered_count(session, player.vk_id)
            empire = await get_empire_status(session)
            cata = await get_cataclysm(session)

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
                from services.shop import bail_cost

                cost = bail_cost(player)
                jail_line = (
                    f"\n🚔 Тюрьма: ещё ~{left} мин"
                    f" · выкуп {cost} крон (🔓 / 🏪 Лавка)"
                )

            eq_line = (
                ", ".join(cat.format_item(it) for it in equipped.values())
                if equipped
                else "пусто"
            )

            progress = "\n".join(
                [
                    _bar("🔥 Стрик", player.daily_streak or 0, 7),
                    _bar("⚔ Победы рейдов", player.raid_wins or 0, 5),
                    _bar("📖 Кодекс", codex_n, 30),
                    _bar("🗺 Квест работ", player.quest_jobs or 0, 10),
                ]
            )
            empire_line = format_empire_line(empire)
            empire_block = f"\n{empire_line}" if empire_line else ""
            cata_line = format_cataclysm(cata)
            cata_block = f"\n{cata_line}" if cata_line else ""
            saga_line = ""
            if int(player.saga_day or 0) > 0:
                saga_line = f"\n📖 Сага: день {min(player.saga_day, 7)}/7"

            text = (
                f"👤 {player.name}\n"
                f"{format_level_line(player)}\n"
                f"💰 Кроны: {player.crowns}\n"
                f"🏛 Налог в казну (неделя МСК): {tax_paid_display(player)}\n"
                f"⚡ Энергия: {player.energy}/{config.MAX_ENERGY} ({energy_hint})\n"
                f"🔥 Стрик ежедневки: {player.daily_streak or 0}\n"
                f"🏅 Титулы: {format_titles(player)}\n"
                f"🛠 {format_professions_line(player)}\n"
                f"📈 Прогресс:\n{progress}\n"
                f"🎒 Экип: {eq_line}\n"
                f"📖 Кодекс: {codex_n}/{cat.catalog_size()}\n"
                f"📨 Код: {player.invite_code}\n"
                f"🏛 Страна: {nation_line}"
                f"{jail_line}"
                f"{empire_block}{cata_block}{saga_line}\n"
                f"{format_event(ev)}\n"
                f"{format_flash_event(flash)}"
            )
            await reply(message, text, keyboard=main_keyboard().get_json())
