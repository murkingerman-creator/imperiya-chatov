from collections.abc import AsyncGenerator
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from bot.config import DB_PATH
from db.models import Base

Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)

engine = create_async_engine(f"sqlite+aiosqlite:///{DB_PATH}", echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

# Soft-migrate columns for existing SQLite DBs on Bothost
_PLAYER_COLS = {
    "last_mine_at": "DATETIME",
    "last_market_at": "DATETIME",
    "last_guard_at": "DATETIME",
    "last_fish_at": "DATETIME",
    "last_farm_at": "DATETIME",
    "last_forge_at": "DATETIME",
    "last_tavern_at": "DATETIME",
    "last_stable_at": "DATETIME",
    "last_smuggle_at": "DATETIME",
    "daily_streak": "INTEGER DEFAULT 0",
    "last_daily_at": "DATETIME",
    "nation_left_at": "DATETIME",
    "invite_code": "VARCHAR(16) DEFAULT ''",
    "referred_by_vk_id": "BIGINT",
    "jail_until": "DATETIME",
    "titles": "VARCHAR(512) DEFAULT ''",
    "quest_jobs": "INTEGER DEFAULT 0",
    "quest_claimed": "INTEGER DEFAULT 0",
    "raid_wins": "INTEGER DEFAULT 0",
    "onboarding_step": "INTEGER DEFAULT 0",
    "last_chat_seen_at": "DATETIME",
    "dm_ok": "INTEGER DEFAULT 1",
    "saga_day": "INTEGER DEFAULT 0",
    "saga_claimed_day": "INTEGER DEFAULT 0",
    "last_protest_at": "DATETIME",
    "xp": "INTEGER DEFAULT 0",
    "level": "INTEGER DEFAULT 1",
    "last_wheel_at": "DATETIME",
    "job_counts": "VARCHAR(512) DEFAULT ''",
    "tax_paid_week": "INTEGER DEFAULT 0",
    "tax_week_key": "VARCHAR(16) DEFAULT ''",
    "work_path": "VARCHAR(32) DEFAULT ''",
    "last_deep_work_at": "DATETIME",
    "order_progress": "VARCHAR(256) DEFAULT ''",
}
_NATION_COLS = {
    "emblem_emoji": "VARCHAR(16) DEFAULT '⚔️'",
    "motto": "VARCHAR(120) DEFAULT ''",
    "capital": "VARCHAR(64) DEFAULT ''",
    "government": "VARCHAR(32) DEFAULT 'республика'",
    "color_tag": "VARCHAR(32) DEFAULT 'лазурь'",
    "anthem": "VARCHAR(120) DEFAULT ''",
    "laws": "VARCHAR(200) DEFAULT ''",
    "welcome": "VARCHAR(120) DEFAULT ''",
    "tax_rate": "FLOAT DEFAULT 0.10",
    "customized_at": "DATETIME",
    "election_at": "DATETIME",
    "shield_until": "DATETIME",
    "shield_pool": "INTEGER DEFAULT 0",
    "work_buff_until": "DATETIME",
    "district_market": "INTEGER DEFAULT 0",
    "district_barracks": "INTEGER DEFAULT 0",
    "district_temple": "INTEGER DEFAULT 0",
    "alliance_cd_until": "DATETIME",
    "muster_until": "DATETIME",
    "continent": "VARCHAR(16) DEFAULT 'center'",
    "discontent": "INTEGER DEFAULT 0",
    "siege_target_id": "INTEGER",
    "siege_progress": "INTEGER DEFAULT 0",
    "siege_attempts": "INTEGER DEFAULT 0",
    "siege_until": "DATETIME",
    "nation_relic": "VARCHAR(64) DEFAULT ''",
    "monument_level": "INTEGER DEFAULT 0",
    "feast_until": "DATETIME",
    "fortify_until": "DATETIME",
    "xp_buff_until": "DATETIME",
    "raid_fund": "INTEGER DEFAULT 0",
    "caravan_progress": "INTEGER DEFAULT 0",
    "caravan_started_at": "DATETIME",
}
_EQUIPPED_COLS = {
    "upgrade": "INTEGER DEFAULT 0",
    "bound": "INTEGER DEFAULT 0",
}
_INVENTORY_COLS = {
    "bound_qty": "INTEGER DEFAULT 0",
    "durability": "INTEGER",
}


async def _ensure_columns(conn, table: str, columns: dict[str, str]) -> None:
    result = await conn.execute(text(f"PRAGMA table_info({table})"))
    existing = {row[1] for row in result.fetchall()}
    for col, decl in columns.items():
        if col not in existing:
            await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {decl}"))


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        try:
            await _ensure_columns(conn, "players", _PLAYER_COLS)
            await _ensure_columns(conn, "nations", _NATION_COLS)
            await _ensure_columns(conn, "equipped_items", _EQUIPPED_COLS)
            await _ensure_columns(conn, "inventory_items", _INVENTORY_COLS)
        except Exception:
            pass


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
