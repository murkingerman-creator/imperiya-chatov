from handlers import (
    admin,
    alliances,
    bugs,
    customize,
    daily,
    districts,
    fun,
    guide,
    inventory,
    invite,
    market,
    nation,
    nation_extra,
    profile,
    shop,
    start,
    suggestions,
    tops,
    war,
    work,
    world_extra,
)


def register_all(bot) -> None:
    start.register(bot)
    guide.register(bot)
    admin.register(bot)
    profile.register(bot)
    daily.register(bot)
    work.register(bot)
    tops.register(bot)
    war.register(bot)
    invite.register(bot)
    customize.register(bot)
    fun.register(bot)
    inventory.register(bot)
    market.register(bot)
    shop.register(bot)
    suggestions.register(bot)
    bugs.register(bot)
    nation.register(bot)
    nation_extra.register(bot)
    districts.register(bot)
    alliances.register(bot)
    world_extra.register(bot)

    # активность в беседе страны → сила рейда
    from db.database import SessionLocal
    from handlers.common import is_chat_peer
    from services.activity import touch_chat_activity
    from services.nation import get_nation_by_chat

    @bot.on.message(blocking=False)
    async def track_chat_activity(message):
        if not is_chat_peer(message.peer_id):
            return
        try:
            async with SessionLocal() as session:
                nation = await get_nation_by_chat(session, message.peer_id)
                if not nation:
                    return
                await touch_chat_activity(session, message.from_id)
        except Exception:
            pass
