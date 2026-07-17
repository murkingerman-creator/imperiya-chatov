import asyncio
import logging

from vkbottle.bot import Bot

from bot.config import GROUP_ID, VK_TOKEN, require_config
from db.database import SessionLocal, init_db
from handlers import register_all
from services.auction import settle_expired_auctions
from services.chatwars import finish_due_wars
from services.chronicle import maybe_post_daily_chronicle, post_flash
from services.notify import post_wall
from services.season import maybe_rotate_season
from services.world_events import ensure_daily_event

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("empire")


async def enable_long_poll(bot: Bot) -> None:
    await bot.api.request(
        "groups.setLongPollSettings",
        {
            "group_id": GROUP_ID,
            "enabled": 1,
            "api_version": "5.199",
            "message_new": 1,
            "message_reply": 1,
            "message_allow": 1,
            "message_deny": 1,
            "message_edit": 1,
            "message_event": 1,
        },
    )
    logger.info("Long Poll API включён для group_id=%s", GROUP_ID)


async def background_loop(bot: Bot) -> None:
    while True:
        try:
            async with SessionLocal() as session:
                await ensure_daily_event(session)
                await settle_expired_auctions(session)
                war_msgs = await finish_due_wars(session)
                for msg in war_msgs:
                    await post_wall(bot.api, msg)
                    await post_flash(bot.api, session, msg)
                    logger.info(msg)
                season_awards = await maybe_rotate_season(session)
                if season_awards:
                    flash = "🏛 Новый сезон!\n" + "\n".join(season_awards)
                    await post_flash(bot.api, session, flash)
                    await post_wall(bot.api, flash)
                posted = await maybe_post_daily_chronicle(bot.api, session)
                if posted:
                    logger.info("Хроника мира опубликована на стену группы")
                await session.commit()
        except Exception as e:
            logger.warning("background_loop: %s", e)
        await asyncio.sleep(15 * 60)


async def main() -> None:
    require_config()
    await init_db()
    bot = Bot(token=VK_TOKEN)
    register_all(bot)
    await enable_long_poll(bot)
    asyncio.create_task(background_loop(bot))
    logger.info("Империя чатов запущена (group_id=%s)", GROUP_ID)
    await bot.run_polling()


if __name__ == "__main__":
    asyncio.run(main())
