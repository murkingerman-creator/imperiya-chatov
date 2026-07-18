import random
from datetime import timedelta

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from bot import config
from content import items_catalog as cat
from db.models import Nation, Player
from services.achievements import format_titles, grant_title
from services.inventory import add_item
from services.player import ensure_aware, utcnow


class AdminError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


async def stats(session: AsyncSession) -> str:
    players = int(
        (await session.execute(select(func.count()).select_from(Player))).scalar_one()
    )
    nations = int(
        (await session.execute(select(func.count()).select_from(Nation))).scalar_one()
    )
    crowns = int(
        (await session.execute(select(func.coalesce(func.sum(Player.crowns), 0)))).scalar_one()
    )
    treasury = int(
        (await session.execute(select(func.coalesce(func.sum(Nation.treasury), 0)))).scalar_one()
    )
    return (
        f"📊 Статистика\n"
        f"Игроков: {players}\n"
        f"Стран: {nations}\n"
        f"Крон у игроков: {crowns}\n"
        f"Казны стран: {treasury}"
    )


async def _get_player(session: AsyncSession, vk_id: int) -> Player:
    result = await session.execute(
        select(Player).options(selectinload(Player.nation)).where(Player.vk_id == vk_id)
    )
    p = result.scalar_one_or_none()
    if not p:
        raise AdminError(f"Игрок {vk_id} не найден.")
    return p


async def get_player_info(session: AsyncSession, vk_id: int) -> str:
    p = await _get_player(session, vk_id)
    nation = "нет"
    if p.nation:
        nation = f"{p.nation.flag_emoji} {p.nation.name} (id={p.nation.id})"
        if p.nation.leader_id == p.vk_id:
            nation += " [лидер]"
    jail = "нет"
    until = ensure_aware(p.jail_until)
    if until and utcnow() < until:
        left = int((until - utcnow()).total_seconds() / 60) + 1
        jail = f"да (~{left} мин)"
    return (
        f"👤 {p.name}\n"
        f"vk_id: {p.vk_id}\n"
        f"💰 {p.crowns} · ⚡ {p.energy}/{config.MAX_ENERGY}\n"
        f"🔥 стрик {p.daily_streak}\n"
        f"⛓ тюрьма: {jail}\n"
        f"🏷 титулы: {format_titles(p)}\n"
        f"📨 {p.invite_code}\n"
        f"🏛 {nation}"
    )


async def give_crowns(session: AsyncSession, vk_id: int, amount: int) -> Player:
    p = await _get_player(session, vk_id)
    p.crowns += amount
    if p.crowns < 0:
        p.crowns = 0
    await session.commit()
    return p


async def take_crowns(session: AsyncSession, vk_id: int, amount: int) -> Player:
    if amount <= 0:
        raise AdminError("Сумма должна быть > 0.")
    p = await _get_player(session, vk_id)
    taken = min(p.crowns, amount)
    p.crowns -= taken
    await session.commit()
    return p


async def give_crowns_all(session: AsyncSession, amount: int) -> dict:
    """Начислить кроны всем игрокам в БД (бонус за обновление)."""
    if amount == 0:
        raise AdminError("Сумма не может быть 0.")
    if abs(amount) > 50_000:
        raise AdminError("Слишком большая сумма (макс ±50000 за раз).")
    count = int(
        (await session.execute(select(func.count()).select_from(Player))).scalar_one()
    )
    if count == 0:
        raise AdminError("В БД нет игроков.")
    await session.execute(update(Player).values(crowns=Player.crowns + amount))
    await session.commit()
    return {"count": count, "amount": amount, "total": count * amount}


async def fill_energy(session: AsyncSession, vk_id: int) -> Player:
    p = await _get_player(session, vk_id)
    p.energy = config.MAX_ENERGY
    p.energy_updated_at = utcnow()
    await session.commit()
    return p


async def fill_energy_all(session: AsyncSession) -> dict:
    count = int(
        (await session.execute(select(func.count()).select_from(Player))).scalar_one()
    )
    if count == 0:
        raise AdminError("В БД нет игроков.")
    await session.execute(
        update(Player).values(energy=config.MAX_ENERGY, energy_updated_at=utcnow())
    )
    await session.commit()
    return {"count": count, "energy": config.MAX_ENERGY}


def _clear_cd_fields(p: Player) -> None:
    p.last_work_at = None
    p.last_mine_at = None
    p.last_market_at = None
    p.last_guard_at = None
    p.last_fish_at = None
    p.last_farm_at = None
    p.last_forge_at = None
    p.last_tavern_at = None
    p.last_smuggle_at = None
    p.last_daily_at = None
    p.nation_left_at = None


async def reset_cooldowns(session: AsyncSession, vk_id: int) -> Player:
    p = await _get_player(session, vk_id)
    _clear_cd_fields(p)
    await session.commit()
    return p


async def reset_cooldowns_all(session: AsyncSession) -> dict:
    result = await session.execute(select(Player))
    players = list(result.scalars().all())
    for p in players:
        _clear_cd_fields(p)
    await session.commit()
    return {"count": len(players)}


async def jail_player(session: AsyncSession, vk_id: int, hours: float) -> Player:
    if hours <= 0:
        raise AdminError("Часы должны быть > 0.")
    if hours > 168:
        raise AdminError("Максимум 168 часов (неделя).")
    p = await _get_player(session, vk_id)
    p.jail_until = utcnow() + timedelta(hours=hours)
    await session.commit()
    return p


async def unjail_player(session: AsyncSession, vk_id: int) -> Player:
    p = await _get_player(session, vk_id)
    p.jail_until = None
    await session.commit()
    return p


async def kick_from_nation(session: AsyncSession, vk_id: int) -> dict:
    p = await _get_player(session, vk_id)
    if not p.nation_id or not p.nation:
        raise AdminError("Игрок не в стране.")
    nation = p.nation
    if nation.leader_id == p.vk_id:
        raise AdminError("Нельзя кикнуть лидера. Сначала удали страну или передай трон.")
    name = f"{nation.flag_emoji} {nation.name}"
    p.nation_id = None
    p.nation_left_at = utcnow()
    await session.commit()
    return {"player": p, "nation": name}


async def give_item_to_player(
    session: AsyncSession, vk_id: int, item_id: str, qty: int = 1
) -> dict:
    if qty < 1 or qty > 50:
        raise AdminError("Кол-во: 1–50.")
    item = cat.get_item(item_id)
    if not item:
        raise AdminError(f"Предмет «{item_id}» не найден.")
    p = await _get_player(session, vk_id)
    await add_item(session, p, item_id, qty)
    await session.commit()
    return {"player": p, "item": item, "qty": qty}


async def give_title_to_player(session: AsyncSession, vk_id: int, code: str) -> dict:
    code = (code or "").strip()
    if code not in config.TITLE_LABELS:
        known = ", ".join(sorted(config.TITLE_LABELS.keys()))
        raise AdminError(f"Неизвестный титул. Известные: {known}")
    p = await _get_player(session, vk_id)
    label = await grant_title(session, p, code)
    if not label:
        raise AdminError(f"У игрока уже есть титул «{config.TITLE_LABELS[code]}».")
    return {"player": p, "title": label}


async def top_rich(session: AsyncSession, limit: int = 15) -> str:
    result = await session.execute(
        select(Player).order_by(Player.crowns.desc(), Player.id.asc()).limit(limit)
    )
    players = list(result.scalars().all())
    if not players:
        return "Игроков нет."
    lines = ["💰 Топ богачей:"]
    for i, p in enumerate(players, 1):
        lines.append(f"{i}. {p.name} (id{p.vk_id}) — {p.crowns}")
    return "\n".join(lines)


async def find_by_name(session: AsyncSession, query: str, limit: int = 12) -> str:
    q = (query or "").strip()
    if len(q) < 2:
        raise AdminError("Минимум 2 символа.")
    result = await session.execute(
        select(Player)
        .where(func.lower(Player.name).like(f"%{q.casefold()}%"))
        .order_by(Player.crowns.desc())
        .limit(limit)
    )
    players = list(result.scalars().all())
    if not players:
        return f"Никого не найдено по «{q}»."
    lines = [f"🔎 Поиск «{q}»:"]
    for p in players:
        lines.append(f"• {p.name} — id{p.vk_id} · {p.crowns} крон")
    return "\n".join(lines)


async def jackpot_random(session: AsyncSession, amount: int) -> dict:
    if amount <= 0:
        raise AdminError("Сумма должна быть > 0.")
    if amount > 100_000:
        raise AdminError("Макс джекпот 100000.")
    result = await session.execute(select(Player))
    players = list(result.scalars().all())
    if not players:
        raise AdminError("Нет игроков.")
    winner = random.choice(players)
    winner.crowns += amount
    await session.commit()
    return {"player": winner, "amount": amount}


async def nation_rain(session: AsyncSession, nation_name: str, amount: int) -> dict:
    if amount <= 0:
        raise AdminError("Сумма должна быть > 0.")
    if amount > 50_000:
        raise AdminError("Макс 50000 на человека.")
    name = (nation_name or "").strip()
    result = await session.execute(
        select(Nation).where(func.lower(Nation.name) == name.casefold())
    )
    nation = result.scalar_one_or_none()
    if not nation:
        raise AdminError(f"Страна «{name}» не найдена.")
    cit = await session.execute(select(Player).where(Player.nation_id == nation.id))
    citizens = list(cit.scalars().all())
    if not citizens:
        raise AdminError("В стране нет граждан.")
    for c in citizens:
        c.crowns += amount
    await session.commit()
    return {
        "nation": nation,
        "amount": amount,
        "count": len(citizens),
        "total": amount * len(citizens),
        "peer_id": nation.chat_peer_id,
    }


async def list_nations_short(session: AsyncSession, limit: int = 15) -> str:
    result = await session.execute(
        select(Nation).order_by(Nation.treasury.desc()).limit(limit)
    )
    nations = list(result.scalars().all())
    if not nations:
        return "Стран нет."
    lines = ["🏛 Страны:"]
    for n in nations:
        lines.append(f"• {n.flag_emoji} {n.name} (id={n.id}) казна={n.treasury}")
    return "\n".join(lines)
