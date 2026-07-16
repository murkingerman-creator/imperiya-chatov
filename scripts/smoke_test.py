import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from db.database import SessionLocal, init_db
from services.economy import do_work
from services.nation import found_nation, get_nation_by_id
from services.player import get_or_create_player
from services.war import raid


async def main() -> None:
    db_path = Path("data/empire.db")
    if db_path.exists():
        db_path.unlink()
    await init_db()
    async with SessionLocal() as s:
        p1 = await get_or_create_player(s, 301, "Alice")
        p2 = await get_or_create_player(s, 302, "Bob")
        await found_nation(s, p1, 2000000021, "North")
        p2 = await get_or_create_player(s, 302, "Bob")
        n2 = await found_nation(s, p2, 2000000022, "South")
        p1 = await get_or_create_player(s, 301, "Alice")
        print("work", await do_work(s, p1))
        south = await get_nation_by_id(s, n2.id)
        assert south is not None
        south.treasury = 500
        await s.commit()
        p1 = await get_or_create_player(s, 301, "Alice")
        res = await raid(s, p1, "South")
        print("raid", res["stolen"], res["treasury_cut"], res["leader_cut"])
        print("OK")


if __name__ == "__main__":
    asyncio.run(main())
