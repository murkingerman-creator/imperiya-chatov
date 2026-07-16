from sqlalchemy.ext.asyncio import AsyncSession

from db.models import ChronicleEvent, MetaKV


async def add_event(
    session: AsyncSession,
    event_type: str,
    text: str,
    nation_ids: str = "",
) -> None:
    session.add(
        ChronicleEvent(event_type=event_type, text=text, nation_ids=nation_ids or "")
    )
    await session.commit()


async def get_meta(session: AsyncSession, key: str, default: str = "") -> str:
    row = await session.get(MetaKV, key)
    return row.value if row else default


async def set_meta(session: AsyncSession, key: str, value: str) -> None:
    row = await session.get(MetaKV, key)
    if row:
        row.value = value
    else:
        session.add(MetaKV(key=key, value=value))
    await session.commit()
