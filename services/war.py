import math
import random
from datetime import timedelta

from sqlalchemy import select
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
from services.roles import can_raid
from services.season import add_points
from services.weeklies import add_progress
from services.flash_events import get_flash_event
from services.alliances import are_allied, get_active_ally
from services.districts import barracks_raid_bonus
from services.muster import active_muster_bonus, consume_muster_after_raid
from services.world_events import (
    get_active_event,
    loot_multiplier,
    raid_blocked,
    raid_cooldown,
    raid_multiplier,
)


class WarError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def _citizen_force(n: int) -> float:
    """Сила от численности: каждый человек важен, сверхрост чуть слабее (√)."""
    n = max(0, n)
    return (
        config.RAID_CITIZEN_WEIGHT * n
        + config.RAID_CITIZEN_SQRT_WEIGHT * math.sqrt(n)
    )


def attack_force(citizens: int, raid_mult: float) -> float:
    gear = max(0.0, float(raid_mult)) * config.RAID_GEAR_ATK_WEIGHT
    return config.RAID_COMBAT_BASE + _citizen_force(citizens) + gear


def defense_force(citizens: int, raid_defend: float) -> float:
    # отрицательный defend (проклятие) ослабляет оборону
    gear = float(raid_defend) * config.RAID_GEAR_DEF_WEIGHT
    return max(0.5, config.RAID_COMBAT_BASE + _citizen_force(citizens) + gear)


def win_chance(atk: float, dfn: float) -> float:
    total = atk + dfn
    if total <= 0:
        return 0.5
    p = atk / total
    return max(config.RAID_WIN_CHANCE_MIN, min(config.RAID_WIN_CHANCE_MAX, p))


def dominance_ratio(atk: float, dfn: float) -> float:
    """0..1 — насколько атака сильнее в паре сил (без clamp шанса)."""
    total = atk + dfn
    if total <= 0:
        return 0.5
    return atk / total


async def nation_manpower(session: AsyncSession, nation_id: int) -> dict:
    """Return total and recently active citizens for combat force calculations."""
    result = await session.execute(
        select(Player).where(Player.nation_id == nation_id)
    )
    citizens = list(result.scalars().all())
    cutoff = utcnow() - timedelta(hours=config.RAID_ACTIVE_HOURS)
    activity_fields = (
        "last_work_at",
        "last_chat_seen_at",
        "last_mine_at",
        "last_market_at",
        "last_guard_at",
        "last_fish_at",
        "last_farm_at",
        "last_forge_at",
        "last_tavern_at",
        "last_stable_at",
        "last_smuggle_at",
    )
    active = sum(
        any(
            (seen := ensure_aware(getattr(player, field, None))) and seen >= cutoff
            for field in activity_fields
        )
        for player in citizens
    )
    total = len(citizens)
    effective = (
        config.RAID_FORCE_ALL_WEIGHT * total
        + config.RAID_FORCE_ACTIVE_WEIGHT * active
    )
    return {"total": total, "active": active, "effective": effective}


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

    if not await can_raid(session, leader):
        raise WarError("Объявлять рейд может только лидер или воевода страны.")

    now = utcnow()
    ev = await get_active_event(session)
    flash = await get_flash_event(session)
    if raid_blocked(ev, flash):
        raise WarError(
            "🕊 Действует мирный договор — рейды временно запрещены."
        )
    loadout = await get_loadout(session, leader)
    charge_notes: list[str] = []

    last = ensure_aware(attacker.last_raid_at)
    cd = raid_cooldown(ev, flash)

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

    if await are_allied(session, attacker.id, defender.id):
        raise WarError("🤝 Нельзя рейдить союзника. Сначала разорвите союз.")

    if defender.treasury < config.RAID_MIN_STEAL:
        raise WarError("У цели почти пустая казна — рейд невыгоден.")

    # defender loadout from their leader for reflect/defend
    def_leader = await session.execute(
        select(Player).where(Player.vk_id == defender.leader_id)
    )
    def_player = def_leader.scalar_one_or_none()
    def_loadout = await get_loadout(session, def_player) if def_player else None

    atk_manpower = await nation_manpower(session, attacker.id)
    def_manpower = await nation_manpower(session, defender.id)

    ally = await get_active_ally(session, attacker.id)
    ally_manpower = None
    effective_atk = float(atk_manpower["effective"])
    if ally:
        ally_manpower = await nation_manpower(session, ally.id)
        effective_atk += float(ally_manpower["effective"]) * float(
            config.ALLIANCE_FORCE_SHARE
        )
        charge_notes.append(
            f"🤝 Союз {ally.flag_emoji} {ally.name}: "
            f"+{int(config.ALLIANCE_FORCE_SHARE * 100)}% силы союзника"
        )

    muster_n, muster_bonus = await active_muster_bonus(session, attacker)
    if muster_bonus:
        effective_atk += muster_bonus
        charge_notes.append(f"📣 Сбор: {muster_n} в строю (+сила)")

    barracks = barracks_raid_bonus(attacker)
    from services.trophies import relic_bonuses

    _, relic_r = relic_bonuses(attacker)
    if barracks:
        charge_notes.append(f"⚔ Казарма: +{int(barracks * 100)}% к атаке")
    if relic_r:
        charge_notes.append(f"🕯 Реликвия: +{int(relic_r * 100)}% к атаке")

    atk_mult = float(getattr(loadout, "raid_mult", 0.0) or 0.0) + barracks + relic_r
    defend_stat = 0.0
    if def_loadout:
        defend_stat = (
            float(def_loadout.raid_defend or 0.0)
            + float(def_loadout.nation_treasury_raid_defend or 0.0)
        )
    fort_until = ensure_aware(defender.fortify_until)
    if fort_until and fort_until > now:
        defend_stat += float(config.TREASURY_FORTIFY_DEFEND)
        charge_notes.append(
            f"🧱 Укрепление цели: +{int(config.TREASURY_FORTIFY_DEFEND * 100)}% защиты"
        )

    atk_pwr = attack_force(effective_atk, atk_mult)
    def_pwr = defense_force(def_manpower["effective"], defend_stat)
    chance = win_chance(atk_pwr, def_pwr)
    dominance = dominance_ratio(atk_pwr, def_pwr)

    from services.item_effects import consume_buff_stack

    if await consume_buff_stack(session, leader.vk_id, "raid_bless"):
        chance = min(
            config.RAID_WIN_CHANCE_MAX,
            chance + config.SHOP_RAID_BLESS_BONUS,
        )
        charge_notes.append(
            f"⚔ Знамя рейда: +{int(config.SHOP_RAID_BLESS_BONUS * 100)}% шанс"
        )
    if await consume_buff_stack(session, leader.vk_id, "hire_blade"):
        chance = min(
            config.RAID_WIN_CHANCE_MAX,
            chance + config.SHOP_HIRE_BLADE_BONUS,
        )
        charge_notes.append(
            f"🗡 Наёмник: +{int(config.SHOP_HIRE_BLADE_BONUS * 100)}% шанс"
        )
    if await consume_buff_stack(session, leader.vk_id, "raid_levy"):
        chance = min(
            config.RAID_WIN_CHANCE_MAX,
            chance + config.TREASURY_WAR_LEVY_BONUS,
        )
        charge_notes.append(
            f"🏛 Военный сбор: +{int(config.TREASURY_WAR_LEVY_BONUS * 100)}% шанс"
        )
    if await consume_buff_stack(session, leader.vk_id, "rumor_raid"):
        chance = min(config.RAID_WIN_CHANCE_MAX, chance + 0.08)
        charge_notes.append("🗣 Слух с работ: +8% шанс рейда")
    shield_until = ensure_aware(defender.shield_until)
    if shield_until and shield_until > now:
        chance = max(
            config.RAID_WIN_CHANCE_MIN,
            min(
                config.RAID_WIN_CHANCE_MAX,
                chance * config.NATION_SHIELD_CHANCE_MULT,
            ),
        )
        charge_notes.append("🛡 Щит страны снизил шанс рейда")

    # КД всегда сгорает — попытка рейда
    attacker.last_raid_at = now
    await add_progress(session, attacker.id, "raid_attempts", 1)
    muster_used = await consume_muster_after_raid(session, attacker)

    from services.siege import apply_siege_on_raid

    rolled = random.random()
    success_roll = rolled <= chance
    siege_info = await apply_siege_on_raid(
        session, attacker, defender, success=success_roll
    )
    if siege_info.get("note"):
        charge_notes.append(siege_info["note"])

    if not success_roll:
        from services.discontent import on_raid_fail
        from services.levels import add_xp

        await on_raid_fail(session, attacker)
        await add_xp(session, leader, config.XP_RAID_FAIL, reason="рейд")
        await add_points(session, defender.id, config.SEASON_RAID_DEFEND)
        await session.commit()
        return {
            "success": False,
            "attacker": attacker,
            "defender": defender,
            "ally": ally,
            "atk_citizens": atk_manpower["effective"],
            "def_citizens": def_manpower["effective"],
            "atk_manpower": atk_manpower,
            "def_manpower": def_manpower,
            "ally_manpower": ally_manpower,
            "atk_power": round(atk_pwr, 1),
            "def_power": round(def_pwr, 1),
            "chance": chance,
            "roll": rolled,
            "charge_notes": charge_notes,
            "muster": muster_used,
            "siege": siege_info,
        }

    # --- победа: доля от казны зависит от перевеса, не чистый рандом ---
    span = config.RAID_STEAL_MAX_PCT - config.RAID_STEAL_MIN_PCT
    pct = config.RAID_STEAL_MIN_PCT + span * dominance
    noise = 1.0 + random.uniform(-config.RAID_STEAL_NOISE, config.RAID_STEAL_NOISE)
    pct = max(config.RAID_STEAL_MIN_PCT * 0.7, min(config.RAID_STEAL_MAX_PCT * 1.15, pct * noise))

    stolen = max(config.RAID_MIN_STEAL, int(defender.treasury * pct))
    stolen = int(stolen * raid_multiplier(ev, flash))
    from services.cataclysm import cataclysm_raid_mult, get_cataclysm

    cata = await get_cataclysm(session)
    stolen = int(stolen * cataclysm_raid_mult(cata))
    stolen = int(stolen * float(siege_info.get("steal_mult") or 1.0))
    if int(attacker.raid_fund or 0) > 0:
        stolen = int(stolen * (1.0 + float(config.TREASURY_RAID_FUND_STEAL)))
        attacker.raid_fund -= 1
        charge_notes.append(
            f"⚔ Фонд рейда: +{int(config.TREASURY_RAID_FUND_STEAL * 100)}% добычи"
        )
    stolen, _ = apply_raid_modifiers(stolen, loadout)

    # доп. срез добычи экипом защиты (поверх уже учтённой силы в шансе)
    if def_loadout and defend_stat > 0:
        stolen = int(stolen * (1.0 - min(0.25, defend_stat * 0.5)))
    elif defend_stat < 0:
        stolen = int(stolen * (1.0 - defend_stat))

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
    rest = stolen - leader_cut
    ally_cut = 0
    if ally:
        ally_cut = int(rest * float(config.ALLIANCE_LOOT_SHARE))
        rest -= ally_cut
    treasury_cut = rest

    defender.treasury -= stolen
    if reflected and def_player:
        defender.treasury += reflected
    attacker.treasury += treasury_cut
    if ally and ally_cut:
        ally.treasury += ally_cut
    leader.crowns += leader_cut
    await add_points(session, attacker.id, config.SEASON_RAID_WIN)

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
    from services.levels import add_xp

    xp_info = await add_xp(session, leader, config.XP_RAID_WIN, reason="рейд")
    if xp_info.get("level_ups"):
        charge_notes.extend(xp_info["level_ups"])
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
        loot_mult=loot_multiplier(ev, flash),
    )

    from services.continents import add_continent_points, ensure_nation_continent
    from services.trophies import maybe_add_trophy

    await ensure_nation_continent(session, attacker)
    await ensure_nation_continent(session, defender)
    await add_continent_points(
        session, attacker, defender, config.CONTINENT_RAID_POINTS
    )
    trophy_hall = await maybe_add_trophy(session, attacker, defender)

    return {
        "success": True,
        "stolen": stolen,
        "leader_cut": leader_cut,
        "treasury_cut": treasury_cut,
        "ally_cut": ally_cut,
        "ally": ally,
        "attacker": attacker,
        "defender": defender,
        "leader_crowns": leader.crowns,
        "titles": titles,
        "trophy": trophy,
        "trophy_hall": trophy_hall,
        "event": ev,
        "drop": drop,
        "charge_notes": charge_notes,
        "reflected": reflected,
        "muster": muster_used,
        "siege": siege_info,
        "atk_citizens": atk_manpower["effective"],
        "def_citizens": def_manpower["effective"],
        "atk_manpower": atk_manpower,
        "def_manpower": def_manpower,
        "ally_manpower": ally_manpower,
        "atk_power": round(atk_pwr, 1),
        "def_power": round(def_pwr, 1),
        "chance": chance,
    }


async def preview_raid_odds(
    session: AsyncSession,
    attacker_nation: Nation,
    defender_nation: Nation,
    leader: Player,
) -> dict:
    """Calculate current odds without spending charges or starting a cooldown."""
    attacker_manpower = await nation_manpower(session, attacker_nation.id)
    defender_manpower = await nation_manpower(session, defender_nation.id)
    loadout = await get_loadout(session, leader)
    result = await session.execute(
        select(Player).where(Player.vk_id == defender_nation.leader_id)
    )
    defender_leader = result.scalar_one_or_none()
    defender_loadout = (
        await get_loadout(session, defender_leader) if defender_leader else None
    )
    defend = 0.0
    if defender_loadout:
        defend = (
            float(defender_loadout.raid_defend or 0.0)
            + float(defender_loadout.nation_treasury_raid_defend or 0.0)
        )
    effective = float(attacker_manpower["effective"])
    ally = await get_active_ally(session, attacker_nation.id)
    ally_manpower = None
    if ally:
        ally_manpower = await nation_manpower(session, ally.id)
        effective += float(ally_manpower["effective"]) * float(
            config.ALLIANCE_FORCE_SHARE
        )
    muster_n, muster_bonus = await active_muster_bonus(session, attacker_nation)
    if muster_bonus:
        effective += muster_bonus
    raid_gear = float(loadout.raid_mult or 0.0) + barracks_raid_bonus(attacker_nation)
    attack = attack_force(effective, raid_gear)
    defense = defense_force(defender_manpower["effective"], defend)
    chance = win_chance(attack, defense)
    shield_until = ensure_aware(defender_nation.shield_until)
    if shield_until and shield_until > utcnow():
        chance = max(
            config.RAID_WIN_CHANCE_MIN,
            min(config.RAID_WIN_CHANCE_MAX, chance * config.NATION_SHIELD_CHANCE_MULT),
        )
    return {
        "chance": chance,
        "atk_power": round(attack, 1),
        "def_power": round(defense, 1),
        "attacker_manpower": attacker_manpower,
        "defender_manpower": defender_manpower,
        "ally": ally,
        "ally_manpower": ally_manpower,
        "muster": muster_n,
        "shielded": bool(shield_until and shield_until > utcnow()),
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
    ally = await get_active_ally(session, exclude_nation_id)
    ally_id = ally.id if ally else None

    # boost marked targets (dawn crown aura) to front
    marked = []
    normal = []
    for n in nations:
        if ally_id and n.id == ally_id:
            continue
        if await _nation_marked(session, n):
            marked.append(n)
        else:
            normal.append(n)
    ordered = marked + normal
    return ordered[:limit]


async def _nation_marked(session: AsyncSession, nation: Nation) -> bool:
    from sqlalchemy import select

    from content import items_catalog as cat
    from db.models import EquippedItem, Player

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
