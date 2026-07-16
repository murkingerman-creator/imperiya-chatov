import asyncio
import logging

from vkbottle.bot import Bot

from bot.config import GROUP_ID, VK_TOKEN, require_config
from db.database import init_db
from handlers import register_all

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("empire")


async def main() -> None:
    require_config()
    await init_db()
    bot = Bot(token=VK_TOKEN)
    register_all(bot)
    logger.info("Империя чатов запущена (group_id=%s)", GROUP_ID)
    await bot.run_polling()


if __name__ == "__main__":
    asyncio.run(main())
