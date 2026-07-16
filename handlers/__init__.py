from handlers import nation, profile, start, tops, war, work


def register_all(bot) -> None:
    start.register(bot)
    profile.register(bot)
    work.register(bot)
    tops.register(bot)
    war.register(bot)
    nation.register(bot)
