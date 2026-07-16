from handlers import nation, profile, start, tops, war, work


def register_all(bot) -> None:
    # Сначала узкие команды, потом война/топ, nation.catch-all с blocking=False
    start.register(bot)
    profile.register(bot)
    work.register(bot)
    tops.register(bot)
    war.register(bot)
    nation.register(bot)
