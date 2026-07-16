import asyncio
import logging

from vkbottle.bot import Bot

from bot.config import GROUP_ID, VK_TOKEN, require_config
from db.database import SessionLocal, init_db
from handlers import register_all
from services.chronicle import maybe_post_daily_chronicle

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


async def chronicle_loop(bot: Bot) -> None:
    while True:
        try:
            async with SessionLocal() as session:
                posted = await maybe_post_daily_chronicle(bot.api, session)
                if posted:
                    logger.info("Хроника мира опубликована на стену группы")
        except Exception as e:
            logger.warning("chronicle_loop: %s", e)
        await asyncio.sleep(15 * 60)


async def main() -> None:
    require_config()
    await init_db()
    bot = Bot(token=VK_TOKEN)
    register_all(bot)
    await enable_long_poll(bot)
    asyncio.create_task(chronicle_loop(bot))
    logger.info("Империя чатов запущена (group_id=%s)", GROUP_ID)
    await bot.run_polling()


if __name__ == "__main__":
    asyncio.run(main())
