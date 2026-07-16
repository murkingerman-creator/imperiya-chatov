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
MAX_ENERGY = 5
ENERGY_REGEN_MINUTES = 20
TAX_RATE = 0.10  # fallback
NATION_FOUND_COST = 50

# Daily
DAILY_BASE = 40
DAILY_STREAK_BONUS = 10
DAILY_STREAK_CAP = 7

# Jobs
JOBS = {
    "mine": {
        "title": "⛏ Шахта",
        "cooldown_min": 90,
        "reward_min": 45,
        "reward_max": 90,
        "success_mult": 1.0,
        "fail_mult": 0.4,
    },
    "market": {
        "title": "🛒 Рынок",
        "cooldown_min": 45,
        "reward_min": 25,
        "reward_max": 50,
        "success_mult": 1.3,
        "fail_mult": 0.6,
    },
    "guard": {
        "title": "🛡 Охрана",
        "cooldown_min": 120,
        "reward_min": 60,
        "reward_max": 120,
        "success_mult": 1.2,
        "fail_mult": 0.5,
        "treasury_bonus": 10,
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

# Legacy alias
WORK_COOLDOWN_MINUTES = 60
WORK_REWARD_MIN = 30
WORK_REWARD_MAX = 60

GOVERNMENTS = ("монархия", "республика", "олигархия", "военная хунта")
COLORS = ("алый", "лазурь", "изумруд", "янтарь", "пурпур", "снег", "обсидиан")
FLAGS = ("🏛", "🏴", "🏳️", "🚩", "🦅", "🐉", "🦁", "🐺", "🦊", "🐻", "🌹", "⭐")
EMBLEMS = ("⚔️", "🛡️", "👑", "🔥", "❄️", "🌙", "☀️", "⚡", "💎", "🏹")


def require_config() -> None:
    if not VK_TOKEN or VK_TOKEN.startswith("vk1.a.your_group_token"):
        raise RuntimeError(
            "Токен VK не задан. На Bothost укажи Bot Token в форме "
            "или переменную VK_TOKEN / BOT_TOKEN. Локально — файл .env."
        )
