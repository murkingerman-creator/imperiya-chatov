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
    "daily_streak": "INTEGER DEFAULT 0",
    "last_daily_at": "DATETIME",
    "nation_left_at": "DATETIME",
    "invite_code": "VARCHAR(16) DEFAULT ''",
    "referred_by_vk_id": "BIGINT",
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
        except Exception:
            pass


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
