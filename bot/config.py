import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _first_env(*names: str) -> str:
    for name in names:
        value = os.getenv(name, "").strip()
        if value:
            return value
    return ""


VK_TOKEN = _first_env("VK_TOKEN", "BOT_TOKEN", "API_TOKEN", "VK_BOT_TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID", "240303101"))

# Admins (creator + deputy). Override via ADMIN_IDS=1,2,3
_DEFAULT_ADMINS = "525336510,784179630"
ADMIN_IDS: set[int] = {
    int(x.strip())
    for x in os.getenv("ADMIN_IDS", _DEFAULT_ADMINS).split(",")
    if x.strip().isdigit()
}


def is_admin(vk_id: int) -> bool:
    return vk_id in ADMIN_IDS


DB_PATH = BASE_DIR / "data" / "empire.db"

# Economy
START_CROWNS = 100
MAX_ENERGY = 8
ENERGY_REGEN_MINUTES = 12
TAX_RATE = 0.10  # fallback
NATION_FOUND_COST = 50

# Daily
DAILY_BASE = 40
DAILY_STREAK_BONUS = 10
DAILY_STREAK_CAP = 7

# Jobs — короткие КД, больше вариантов (чтобы не «ждать-ждать»)
JOBS = {
    "mine": {
        "title": "⛏ Шахта",
        "cooldown_min": 35,
        "reward_min": 40,
        "reward_max": 85,
        "success_mult": 1.0,
        "fail_mult": 0.4,
        "loot_pool": "mine",
    },
    "market": {
        "title": "🛒 Рынок",
        "cooldown_min": 18,
        "reward_min": 22,
        "reward_max": 48,
        "success_mult": 1.3,
        "fail_mult": 0.6,
        "loot_pool": "market",
    },
    "guard": {
        "title": "🛡 Охрана",
        "cooldown_min": 40,
        "reward_min": 50,
        "reward_max": 100,
        "success_mult": 1.2,
        "fail_mult": 0.5,
        "treasury_bonus": 10,
        "loot_pool": "guard",
    },
    "fish": {
        "title": "🎣 Рыбалка",
        "cooldown_min": 12,
        "reward_min": 15,
        "reward_max": 35,
        "success_mult": 1.2,
        "fail_mult": 0.5,
        "loot_pool": "mine",
    },
    "farm": {
        "title": "🌾 Поле",
        "cooldown_min": 16,
        "reward_min": 18,
        "reward_max": 40,
        "success_mult": 1.15,
        "fail_mult": 0.55,
        "loot_pool": "market",
    },
    "forge": {
        "title": "🔥 Кузня",
        "cooldown_min": 28,
        "reward_min": 35,
        "reward_max": 75,
        "success_mult": 1.25,
        "fail_mult": 0.45,
        "loot_pool": "guard",
    },
    "tavern": {
        "title": "🍺 Таверна",
        "cooldown_min": 10,
        "reward_min": 12,
        "reward_max": 28,
        "success_mult": 1.35,
        "fail_mult": 0.5,
        "loot_pool": "market",
    },
}

# Nation
NATION_SWITCH_COOLDOWN_HOURS = 24
CUSTOMIZE_COOLDOWN_HOURS = 6
CUSTOMIZE_CHANGE_COST = 20
TAX_PRESETS = (0.05, 0.10, 0.15, 0.20)

# Invite
INVITE_INVITER_REWARD = 80
INVITE_INVITEE_REWARD = 40
INVITE_TREASURY_REWARD = 50

# War
RAID_COOLDOWN_HOURS = 3
RAID_STEAL_MIN_PCT = 0.05
RAID_STEAL_MAX_PCT = 0.15
RAID_MIN_STEAL = 10
RAID_LEADER_SHARE = 0.30
RAID_TREASURY_SHARE = 0.70
RAID_NIGHT_COOLDOWN_MINUTES = 15  # during raid night
# Combat: сила = база + вес*граждане + √-бонус + экип
RAID_COMBAT_BASE = 3.0
RAID_CITIZEN_WEIGHT = 1.15       # линейно за человека
RAID_CITIZEN_SQRT_WEIGHT = 1.2   # доп. с убывающей отдачей
RAID_GEAR_ATK_WEIGHT = 10.0   # * raid_mult лидера
RAID_GEAR_DEF_WEIGHT = 14.0   # * raid_defend лидера/ауры
RAID_WIN_CHANCE_MIN = 0.15
RAID_WIN_CHANCE_MAX = 0.90
RAID_STEAL_NOISE = 0.08  # ± шум к доле после учёта перевеса

# Smuggle
SMUGGLE_COOLDOWN_MIN = 35
SMUGGLE_SUCCESS_CHANCE = 0.45
SMUGGLE_REWARD_MIN = 80
SMUGGLE_REWARD_MAX = 200
SMUGGLE_JAIL_HOURS = 1

# Duels
DUEL_MIN_BET = 20
DUEL_MAX_BET = 500
DUEL_TTL_SEC = 120

# Elections
ELECTION_DAYS = 7

# Quests
QUEST_JOBS_NEEDED = 3
QUEST_REWARD_MIN = 100
QUEST_REWARD_MAX = 180

# Auction
AUCTION_HOURS = 6
AUCTION_START_BID = 50
TROPHY_CHANCE = 0.35

# Chat war
CHAT_WAR_HOURS = 24
CHAT_WAR_STAKE = 150

# Legacy alias
WORK_COOLDOWN_MINUTES = 60
WORK_REWARD_MIN = 30
WORK_REWARD_MAX = 60

GOVERNMENTS = ("монархия", "республика", "олигархия", "военная хунта")
COLORS = ("алый", "лазурь", "изумруд", "янтарь", "пурпур", "снег", "обсидиан")
FLAGS = ("🏛", "🏴", "🏳️", "🚩", "🦅", "🐉", "🦁", "🐺", "🦊", "🐻", "🌹", "⭐")
EMBLEMS = ("⚔️", "🛡️", "👑", "🔥", "❄️", "🌙", "☀️", "⚡", "💎", "🏹")

WORLD_EVENTS = {
    "plague": {
        "title": "🕷 Чума",
        "desc": "Доход с работ −40%, налог стран +5 п.п.",
        "work_mult": 0.6,
        "tax_add": 0.05,
        "raid_mult": 1.0,
        "raid_cd_mult": 1.0,
    },
    "fair": {
        "title": "🎪 Ярмарка",
        "desc": "Доход с работ +30%, рейды −20% добычи",
        "work_mult": 1.3,
        "tax_add": 0.0,
        "raid_mult": 0.8,
        "raid_cd_mult": 1.0,
    },
    "revolt": {
        "title": "🔥 Восстание",
        "desc": "Рейды +40% добычи, кулдаун рейда быстрее",
        "work_mult": 0.9,
        "tax_add": -0.02,
        "raid_mult": 1.4,
        "raid_cd_mult": 0.7,
    },
    "gold_vein": {
        "title": "✨ Золотая жила",
        "desc": "Доход с работ +50%",
        "work_mult": 1.5,
        "tax_add": 0.0,
        "raid_mult": 1.0,
        "raid_cd_mult": 1.0,
    },
    "raid_night": {
        "title": "🌙 Ночь рейдов",
        "desc": "Кулдаун рейда 15 минут!",
        "work_mult": 1.0,
        "tax_add": 0.0,
        "raid_mult": 1.15,
        "raid_cd_mult": 0.0,  # special: use RAID_NIGHT minutes
        "raid_night": True,
    },
}

TITLE_LABELS = {
    "first_raid": "⚔ Первый рейд",
    "streak_7": "🔥 Стрик 7",
    "treasury_10k": "🏦 Казна 10к",
    "smuggler": "🕶 Контрабандист",
    "duelist": "🥊 Дуэлянт",
    "questor": "🗺 Квестовик",
    "emperor": "👑 Император выборов",
    "collector": "📦 Коллекционер",
    "myth_finder": "🟥 Искатель мифов",
}

# Arsenal / loot
LOOT_CHANCE_SUCCESS = 0.12
LOOT_CHANCE_FAIL = 0.05
LOOT_GUARD_SUCCESS_BONUS = 0.03
LOOT_SMUGGLE_SUCCESS = 0.15
LOOT_RAID_CHANCE = 0.08
LOOT_RARITY_WEIGHTS = {
    "common": 70.0,
    "uncommon": 20.0,
    "rare": 7.0,
    "epic": 2.2,
    "legendary": 0.7,
    "mythic": 0.1,
}
WORK_MULT_CAP = 0.35
RAID_MULT_CAP = 0.25
MERGE_COMMON_COUNT = 3

# Player marketplace
MARKET_FEE = 0.05  # 5% с продавца
MARKET_MIN_PRICE = 10
MARKET_MAX_PRICE = 50000
MARKET_MAX_LISTINGS = 10
MARKET_HOURS = 72


def require_config() -> None:
    if not VK_TOKEN or VK_TOKEN.startswith("vk1.a.your_group_token"):
        raise RuntimeError(
            "Токен VK не задан. На Bothost укажи Bot Token в форме "
            "или переменную VK_TOKEN / BOT_TOKEN. Локально — файл .env."
        )
