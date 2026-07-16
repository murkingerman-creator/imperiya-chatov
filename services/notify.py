import logging
import random

from vkbottle import API

from bot.config import GROUP_ID

logger = logging.getLogger("empire.notify")


async def send_to_peer(api: API, peer_id: int, text: str) -> None:
    try:
        await api.messages.send(
            peer_id=peer_id,
            message=text,
            random_id=random.randint(1, 2_000_000_000),
        )
    except Exception as e:
        logger.warning("notify peer %s failed: %s", peer_id, e)


async def notify_nation_chat(api: API, chat_peer_id: int, text: str) -> None:
    await send_to_peer(api, chat_peer_id, text)


async def post_wall(api: API, text: str) -> None:
    try:
        await api.wall.post(owner_id=-GROUP_ID, from_group=1, message=text)
    except Exception as e:
        logger.warning("wall.post failed: %s", e)
