from vkbottle.bot import Bot, Message

from bot import config
from bot.keyboards import main_keyboard, onboarding_keyboard
from db.database import SessionLocal
from handlers.common import reply, resolve_name
from handlers.rules import match_cmd
from services.achievements import check_streak
from services.announce import announce_nation
from services.daily import DailyError, claim_daily
from services.onboarding import advance_onboarding, onboarding_prompt
from services.player import get_or_create_player


def register(bot: Bot) -> None:
    @bot.on.message(func=match_cmd("daily", "ежедневка", "🎁 ежедневка", "бонус"))
    async def daily_handler(message: Message):
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            try:
                result = await claim_daily(session, player)
            except DailyError as e:
                await reply(message, e.message, keyboard=main_keyboard().get_json())
                return

            # Награда уже в БД — ответ игроку не должен пропасть из‑за XP/титулов
            title_line = ""
            xp_line = ""
            onboard_line = ""
            try:
                titles = await check_streak(session, player)
                if titles:
                    title_line = f"\n🏅 {', '.join(titles)}"
                from services.levels import add_xp

                xp_info = await add_xp(
                    session, player, config.XP_DAILY, reason="ежедневка"
                )
                if xp_info.get("level_ups"):
                    xp_line = "\n" + "\n".join(xp_info["level_ups"])
                elif xp_info.get("gained"):
                    xp_line = f"\n⭐ +{xp_info['gained']} XP"
                onboard = await advance_onboarding(session, player, "daily")
                if onboard:
                    onboard_line = f"\n{onboard}"
            except Exception:
                xp_line = (
                    "\n⚠ Бонус XP мог не начислиться — кроны уже на балансе "
                    "(👤 Профиль)."
                )

            text = (
                f"🎁 Ежедневка получена!\n"
                f"+{result['reward']} крон "
                f"(база {result['base']} + стрик {result['bonus']})\n"
                f"🔥 Стрик: {result['streak']} дн.\n"
                f"💰 Баланс: {result['crowns']}{title_line}{xp_line}{onboard_line}"
            )
            await announce_nation(
                message.ctx_api,
                player.nation,
                f"🎁 {player.name}: ежедневка (+{result['reward']})",
            )
            step = player.onboarding_step or 0
            kb = (
                onboarding_keyboard(step).get_json()
                if step and onboarding_prompt(player)
                else main_keyboard().get_json()
            )
            await reply(message, text, keyboard=kb)
