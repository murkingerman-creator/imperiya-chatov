from datetime import timedelta

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from bot import config
from db.models import InviteUse, Nation, Player, WarLog
from services.player import ensure_aware, regenerate_energy, utcnow


class NationError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


CHAT_PEER_OFFSET = 2_000_000_000


def is_chat_peer(peer_id: int) -> bool:
    return peer_id >= CHAT_PEER_OFFSET


def format_nation_card(
    nation: Nation, citizens: int, *, ally_line: str | None = None
) -> str:
    lines = [
        f"{nation.flag_emoji} {nation.name}",
        f"Герб: {nation.emblem_emoji} · Цвет: {nation.color_tag}",
        f"Строй: {nation.government}",
    ]
    if nation.capital:
        lines.append(f"Столица: {nation.capital}")
    if nation.motto:
        lines.append(f'Девиз: «{nation.motto}»')
    if nation.anthem:
        lines.append(f"Гимн: {nation.anthem}")
    if nation.laws:
        lines.append(f"Законы: {nation.laws}")
    if nation.welcome:
        lines.append(f"Приветствие: {nation.welcome}")
    tax_pct = int(round((nation.tax_rate or 0.1) * 100))
    lines.append(f"💰 Казна: {nation.treasury} · Налог: {tax_pct}% · 👥 {citizens}")
    from services.districts import districts_card_line

    lines.append(districts_card_line(nation))
    if ally_line:
        lines.append(ally_line)
    return "\n".join(lines)


async def get_nation_by_chat(session: AsyncSession, peer_id: int) -> Nation | None:
    result = await session.execute(
        select(Nation)
        .options(selectinload(Nation.players))
        .where(Nation.chat_peer_id == peer_id)
    )
    return result.scalar_one_or_none()


async def get_nation_by_id(session: AsyncSession, nation_id: int) -> Nation | None:
    result = await session.execute(
        select(Nation)
        .options(selectinload(Nation.players))
        .where(Nation.id == nation_id)
    )
    return result.scalar_one_or_none()


async def get_nation_by_name(session: AsyncSession, name: str) -> Nation | None:
    needle = name.strip().casefold()
    if not needle:
        return None
    # SQLite lower() не умеет кириллицу — сравниваем в Python
    result = await session.execute(
        select(Nation).options(selectinload(Nation.players))
    )
    for nation in result.scalars().all():
        if nation.name.casefold() == needle:
            return nation
    return None


async def find_nations_fuzzy(session: AsyncSession, query: str) -> list[Nation]:
    """Точное имя, id=N или частичное совпадение."""
    q = query.strip()
    if not q:
        return []
    if q.isdigit():
        nation = await get_nation_by_id(session, int(q))
        return [nation] if nation else []
    if q.lower().startswith("id=") and q[3:].strip().isdigit():
        nation = await get_nation_by_id(session, int(q[3:].strip()))
        return [nation] if nation else []

    exact = await get_nation_by_name(session, q)
    if exact:
        return [exact]

    needle = q.casefold()
    result = await session.execute(select(Nation))
    return [n for n in result.scalars().all() if needle in n.name.casefold()]


async def count_citizens(session: AsyncSession, nation_id: int) -> int:
    result = await session.execute(
        select(func.count()).select_from(Player).where(Player.nation_id == nation_id)
    )
    return int(result.scalar_one())


def _check_switch_cooldown(player: Player) -> None:
    left = ensure_aware(player.nation_left_at)
    if not left:
        return
    ready = left + timedelta(hours=config.NATION_SWITCH_COOLDOWN_HOURS)
    now = utcnow()
    if now < ready:
        hours = (ready - now).total_seconds() / 3600
        raise NationError(
            f"Смена страны на кулдауне. Подожди ещё ~{hours:.1f} ч."
        )


async def found_nation(
    session: AsyncSession,
    player: Player,
    peer_id: int,
    name: str,
    flag_emoji: str = "🏛",
) -> Nation:
    regenerate_energy(player)

    if not is_chat_peer(peer_id):
        raise NationError("Основать страну можно только в беседе. Добавь бота в чат.")

    name = name.strip()
    if len(name) < 2 or len(name) > 32:
        raise NationError("Название страны: от 2 до 32 символов.")

    if player.nation_id:
        raise NationError("Ты уже гражданин страны. Сначала выйди (🚪 Выйти).")

    _check_switch_cooldown(player)

    existing = await get_nation_by_chat(session, peer_id)
    if existing:
        raise NationError(
            f"В этой беседе уже есть страна «{existing.flag_emoji} {existing.name}»."
        )

    if await get_nation_by_name(session, name):
        raise NationError("Страна с таким названием уже существует.")

    if player.crowns < config.NATION_FOUND_COST:
        raise NationError(
            f"Нужно {config.NATION_FOUND_COST} крон для основания (у тебя {player.crowns})."
        )

    player.crowns -= config.NATION_FOUND_COST
    nation = Nation(
        chat_peer_id=peer_id,
        name=name,
        flag_emoji=flag_emoji or "🏛",
        emblem_emoji="⚔️",
        leader_id=player.vk_id,
        treasury=0,
        tax_rate=0.10,
        government="республика",
        color_tag="лазурь",
    )
    session.add(nation)
    await session.flush()
    player.nation_id = nation.id
    await session.commit()
    await session.refresh(player, attribute_names=["nation"])
    await session.refresh(nation)
    return nation


async def join_nation(session: AsyncSession, player: Player, peer_id: int) -> Nation:
    if not is_chat_peer(peer_id):
        raise NationError("Вступить можно только из беседы своей будущей страны.")

    if player.nation_id:
        raise NationError("Ты уже состоишь в стране. Сначала выйди.")

    _check_switch_cooldown(player)

    nation = await get_nation_by_chat(session, peer_id)
    if not nation:
        raise NationError("В этой беседе ещё нет страны. Оснуй её кнопкой «Основать».")

    player.nation_id = nation.id
    await session.commit()
    await session.refresh(player, attribute_names=["nation"])
    return nation


async def leave_nation(session: AsyncSession, player: Player) -> str:
    if not player.nation_id or not player.nation:
        raise NationError("Ты не состоишь в стране.")

    nation = player.nation
    if nation.leader_id == player.vk_id:
        citizens = await count_citizens(session, nation.id)
        if citizens > 1:
            raise NationError(
                "Лидер не может выйти, пока есть граждане. "
                "Передай трон (👑) или распусти страну (🗑)."
            )
        # sole leader — auto dissolve
        name = await dissolve_nation(session, player)
        return f"Ты был единственным гражданином. Страна «{name}» распущена."

    nation_name = f"{nation.flag_emoji} {nation.name}"
    player.nation_id = None
    player.nation_left_at = utcnow()
    await session.commit()
    return f"Ты покинул {nation_name}. Вступить в другую можно через 24 ч."


async def transfer_leadership(
    session: AsyncSession, leader: Player, target_vk_id: int
) -> Player:
    if not leader.nation_id or not leader.nation:
        raise NationError("Ты не в стране.")
    if leader.nation.leader_id != leader.vk_id:
        raise NationError("Передать трон может только лидер.")

    result = await session.execute(
        select(Player).where(
            Player.vk_id == target_vk_id, Player.nation_id == leader.nation_id
        )
    )
    target = result.scalar_one_or_none()
    if not target:
        raise NationError("Игрок не найден среди граждан твоей страны.")
    if target.vk_id == leader.vk_id:
        raise NationError("Нельзя передать трон самому себе.")

    leader.nation.leader_id = target.vk_id
    await session.commit()
    return target


async def dissolve_nation(session: AsyncSession, leader: Player) -> str:
    """Полностью удаляет страну (для тестов и лидера)."""
    if not leader.nation_id or not leader.nation:
        raise NationError("Ты не в стране.")
    nation = await get_nation_by_id(session, leader.nation_id)
    if not nation:
        raise NationError("Страна не найдена.")
    if nation.leader_id != leader.vk_id:
        raise NationError("Распустить страну может только лидер.")
    return await dissolve_nation_by_id(session, nation.id)


async def dissolve_nation_by_id(session: AsyncSession, nation_id: int) -> str:
    nation = await get_nation_by_id(session, nation_id)
    if not nation:
        raise NationError("Страна не найдена.")

    nation_name = f"{nation.flag_emoji} {nation.name}"

    await session.execute(
        update(Player)
        .where(Player.nation_id == nation_id)
        .values(nation_id=None, nation_left_at=utcnow())
    )
    await session.execute(
        delete(WarLog).where(
            (WarLog.attacker_nation_id == nation_id)
            | (WarLog.defender_nation_id == nation_id)
        )
    )
    await session.delete(nation)
    await session.commit()
    return nation_name


async def dissolve_nation_by_name(session: AsyncSession, name: str) -> str:
    matches = await find_nations_fuzzy(session, name)
    if not matches:
        raise NationError(
            f"Страна «{name}» не найдена.\n"
            "Открой «Список стран» и удали по id, например: 1"
        )
    if len(matches) > 1:
        lines = ["Найдено несколько, уточни id или точное имя:"]
        for n in matches[:10]:
            lines.append(f"• id={n.id} {n.flag_emoji} {n.name}")
        raise NationError("\n".join(lines))
    return await dissolve_nation_by_id(session, matches[0].id)

async def list_citizens(session: AsyncSession, nation_id: int, limit: int = 6) -> list[Player]:
    result = await session.execute(
        select(Player)
        .where(Player.nation_id == nation_id)
        .order_by(Player.created_at.asc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def apply_invite(
    session: AsyncSession, invitee: Player, code: str
) -> dict:
    code = code.strip().upper()
    if invitee.nation_id:
        raise NationError("Сначала выйди из своей страны.")

    existing = await session.execute(
        select(InviteUse).where(InviteUse.invitee_vk_id == invitee.vk_id)
    )
    if existing.scalar_one_or_none():
        raise NationError("Ты уже использовал инвайт ранее.")

    result = await session.execute(
        select(Player)
        .options(selectinload(Player.nation))
        .where(Player.invite_code == code)
    )
    inviter = result.scalar_one_or_none()
    if not inviter:
        raise NationError("Код инвайта не найден.")
    if inviter.vk_id == invitee.vk_id:
        raise NationError("Нельзя использовать свой код.")

    _check_switch_cooldown(invitee)

    nation = inviter.nation
    joined_nation = None
    if nation:
        invitee.nation_id = nation.id
        joined_nation = nation
        nation.treasury += config.INVITE_TREASURY_REWARD

    invitee.referred_by_vk_id = inviter.vk_id
    invitee.crowns += config.INVITE_INVITEE_REWARD
    inviter.crowns += config.INVITE_INVITER_REWARD

    session.add(
        InviteUse(
            inviter_vk_id=inviter.vk_id,
            invitee_vk_id=invitee.vk_id,
            nation_id=joined_nation.id if joined_nation else None,
            reward_paid=True,
        )
    )
    await session.commit()
    if joined_nation:
        await session.refresh(joined_nation)

    return {
        "inviter": inviter,
        "invitee_reward": config.INVITE_INVITEE_REWARD,
        "inviter_reward": config.INVITE_INVITER_REWARD,
        "treasury_reward": config.INVITE_TREASURY_REWARD if joined_nation else 0,
        "nation": joined_nation,
    }


async def list_nations_short_names(
    session: AsyncSession, *, exclude_id: int | None = None, limit: int = 12
) -> list[str]:
    """Короткие имена стран для кнопок (по казне)."""
    result = await session.execute(
        select(Nation).order_by(Nation.treasury.desc(), Nation.id.asc()).limit(limit + 2)
    )
    names: list[str] = []
    for n in result.scalars().all():
        if exclude_id is not None and n.id == exclude_id:
            continue
        names.append(n.name)
        if len(names) >= limit:
            break
    return names


async def top_nations(session: AsyncSession, limit: int = 10) -> list[tuple[Nation, int]]:
    citizens = (
        select(Player.nation_id, func.count().label("cnt"))
        .where(Player.nation_id.is_not(None))
        .group_by(Player.nation_id)
        .subquery()
    )
    result = await session.execute(
        select(Nation, func.coalesce(citizens.c.cnt, 0))
        .outerjoin(citizens, Nation.id == citizens.c.nation_id)
        .order_by(Nation.treasury.desc(), Nation.id.asc())
        .limit(limit)
    )
    return list(result.all())


async def top_players(session: AsyncSession, limit: int = 10) -> list[Player]:
    result = await session.execute(
        select(Player).order_by(Player.crowns.desc(), Player.id.asc()).limit(limit)
    )
    return list(result.scalars().all())
