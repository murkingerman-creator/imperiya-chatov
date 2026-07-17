from handlers import (
    admin,
    customize,
    daily,
    fun,
    guide,
    inventory,
    invite,
    market,
    nation,
    profile,
    shop,
    start,
    tops,
    war,
    work,
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
    nation.register(bot)
