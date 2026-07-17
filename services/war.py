import random
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from bot import config
from db.models import Nation, Player, WarLog
from services.achievements import check_after_raid, check_treasury
from services.auction import maybe_create_trophy
from services.chatwars import add_score
from services.item_effects import apply_raid_modifiers, get_loadout, try_consume_charge
from services.loot import grant_drop
from services.nation import get_nation_by_id, get_nation_by_name
from services.player import ensure_aware, utcnow
from services.world_events import get_active_event, raid_cooldown, raid_multiplier


class WarError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


async def raid(
    session: AsyncSession,
    leader: Player,
    target_name: str,
) -> dict:
    if not leader.nation_id or not leader.nation:
        raise WarError("Сначала вступи в страну или оснуй её.")

    attacker = await get_nation_by_id(session, leader.nation_id)
    if not attacker:
        raise WarError("Страна не найдена.")

    if attacker.leader_id != leader.vk_id:
        raise WarError("Объявлять рейд может только лидер страны.")

    now = utcnow()
    ev = await get_active_event(session)
    loadout = await get_loadout(session, leader)
    charge_notes: list[str] = []

    last = ensure_aware(attacker.last_raid_at)
    cd = raid_cooldown(ev)

    # raid_night_once: treat CD as 15 min for this raid check
    if last and "raid_night_once" in loadout.charges_ready:
        night_cd = timedelta(minutes=config.RAID_NIGHT_COOLDOWN_MINUTES)
        if now >= last + night_cd:
            name = await try_consume_charge(session, leader, "raid_night_once", loadout)
            if name:
                cd = night_cd
                charge_notes.append(f"⚡ {name}: ночной КД")
                loadout = await get_loadout(session, leader)

    # raid_cd_minus_1h: reduce effective CD when checking
    if "raid_cd_minus_1h" in loadout.charges_ready and last:
        reduced = cd - timedelta(hours=1)
        if reduced.total_seconds() < 0:
            reduced = timedelta(minutes=15)
        if now >= last + reduced:
            name = await try_consume_charge(session, leader, "raid_cd_minus_1h", loadout)
            if name:
                cd = reduced
                charge_notes.append(f"⚡ {name}: КД −1ч")
                loadout = await get_loadout(session, leader)

    # passive raid_cd_hours from loadout
    if loadout.raid_cd_hours:
        cd = cd + timedelta(hours=loadout.raid_cd_hours)
        if cd.total_seconds() < 900:
            cd = timedelta(minutes=15)

    if last:
        ready_at = last + cd
        if now < ready_at:
            left = (ready_at - now).total_seconds()
            if left >= 3600:
                raise WarError(f"Рейд на перезарядке. Осталось ~{left/3600:.1f} ч.")
            raise WarError(f"Рейд на перезарядке. Осталось ~{int(left/60)+1} мин.")

    defender = await get_nation_by_name(session, target_name)
    if not defender:
        raise WarError(f"Страна «{target_name}» не найдена.")

    if defender.id == attacker.id:
        raise WarError("Нельзя напасть на свою страну.")

    if defender.treasury < config.RAID_MIN_STEAL:
        raise WarError("У цели почти пустая казна — рейд невыгоден.")

    # defender loadout from their leader for reflect/defend
    from sqlalchemy import select

    def_leader = await session.execute(
        select(Player).where(Player.vk_id == defender.leader_id)
    )
    def_player = def_leader.scalar_one_or_none()
    def_loadout = await get_loadout(session, def_player) if def_player else None

    pct = random.uniform(config.RAID_STEAL_MIN_PCT, config.RAID_STEAL_MAX_PCT)
    stolen = max(config.RAID_MIN_STEAL, int(defender.treasury * pct))
    stolen = int(stolen * raid_multiplier(ev))
    stolen, _ = apply_raid_modifiers(stolen, loadout)

    defend = 0.0
    if def_loadout:
        defend = def_loadout.raid_defend + def_loadout.nation_treasury_raid_defend
        # cursed black mark: negative defend on victim = more stolen
        if defend < 0:
            stolen = int(stolen * (1.0 - defend))
            defend = 0.0
        else:
            stolen = int(stolen * (1.0 - min(0.35, defend)))

    stolen = min(stolen, defender.treasury)

    # reflect charge on defender
    reflected = 0
    if def_player and def_loadout and "raid_reflect" in def_loadout.charges_ready:
        if random.random() < 0.35:
            name = await try_consume_charge(
                session, def_player, "raid_reflect", def_loadout
            )
            if name:
                reflected = max(1, int(stolen * 0.4))
                stolen -= reflected
                charge_notes.append(f"🛡 {name}: отражено {reflected}")

    share = config.RAID_LEADER_SHARE + loadout.raid_leader_share
    share = max(0.15, min(0.5, share))
    leader_cut = int(stolen * share)
    treasury_cut = stolen - leader_cut

    defender.treasury -= stolen
    if reflected and def_player:
        defender.treasury += reflected
    attacker.treasury += treasury_cut
    leader.crowns += leader_cut
    attacker.last_raid_at = now

    session.add(
        WarLog(
            attacker_nation_id=attacker.id,
            defender_nation_id=defender.id,
            amount=stolen,
        )
    )
    await session.commit()

    titles = await check_after_raid(session, leader)
    titles += await check_treasury(session, leader)
    trophy = await maybe_create_trophy(session, attacker)

    score_pts = 1
    if "war_score_bonus" in loadout.charges_ready:
        name = await try_consume_charge(session, leader, "war_score_bonus", loadout)
        if name:
            score_pts = 2
            charge_notes.append(f"⚡ {name}: +2 очка войны")
    await add_score(session, attacker.id, score_pts)

    drop = await grant_drop(
        session,
        leader,
        "raid",
        success=True,
        loot_luck=loadout.loot_luck,
    )

    return {
        "stolen": stolen,
        "leader_cut": leader_cut,
        "treasury_cut": treasury_cut,
        "attacker": attacker,
        "defender": defender,
        "leader_crowns": leader.crowns,
        "titles": titles,
        "trophy": trophy,
        "event": ev,
        "drop": drop,
        "charge_notes": charge_notes,
        "reflected": reflected,
    }


async def raid_candidates(
    session: AsyncSession, exclude_nation_id: int, limit: int = 6
) -> list[Nation]:
    from sqlalchemy import select

    result = await session.execute(
        select(Nation)
        .where(Nation.id != exclude_nation_id, Nation.treasury >= config.RAID_MIN_STEAL)
        .order_by(Nation.treasury.desc())
        .limit(limit * 2)
    )
    nations = list(result.scalars().all())

    # boost marked targets (dawn crown aura) to front
    marked = []
    normal = []
    for n in nations:
        if await _nation_marked(session, n):
            marked.append(n)
        else:
            normal.append(n)
    ordered = marked + normal
    return ordered[:limit]


async def _nation_marked(session: AsyncSession, nation: Nation) -> bool:
    from sqlalchemy import select

    from db.models import EquippedItem, Player
    from content import items_catalog as cat

    result = await session.execute(
        select(Player.vk_id).where(Player.nation_id == nation.id)
    )
    vk_ids = [r[0] for r in result.all()]
    if not vk_ids:
        return False
    eq = await session.execute(
        select(EquippedItem).where(EquippedItem.player_vk_id.in_(vk_ids))
    )
    for row in eq.scalars().all():
        it = cat.get_item(row.item_id)
        if it and (it.get("aura") or {}).get("raid_target_mark"):
            return True
    return False
