"""Пассивы экипировки, ауры нации, заряды легенд/мифов."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot import config
from content import items_catalog as cat
from db.models import EquippedItem, ItemCharge, Player, PlayerBuff
from services.player import ensure_aware, utcnow


@dataclass
class Loadout:
    items: list[dict] = field(default_factory=list)
    work_mult: float = 0.0
    job_bonus: dict = field(default_factory=dict)
    raid_mult: float = 0.0
    raid_defend: float = 0.0
    raid_cd_hours: float = 0.0
    raid_leader_share: float = 0.0
    tax_add: float = 0.0
    smuggle_chance: float = 0.0
    smuggle_reward: float = 0.0
    smuggle_fine_mult: float = 1.0
    jail_hours_mult: float = 1.0
    treasury_bonus_add: int = 0
    loot_luck: float = 0.0
    nation_work_mult: float = 0.0
    personal_gold_vein: bool = False
    raid_target_mark: bool = False
    nation_treasury_raid_defend: float = 0.0
    charges_ready: dict[str, str] = field(default_factory=dict)  # code -> item_id


async def get_loadout(session: AsyncSession, player: Player) -> Loadout:
    result = await session.execute(
        select(EquippedItem).where(EquippedItem.player_vk_id == player.vk_id)
    )
    equipped = []
    for row in result.scalars().all():
        item = cat.get_item(row.item_id)
        if not item:
            continue
        item = dict(item)
        item["_upgrade"] = row.upgrade or 0
        equipped.append(item)
    loadout = Loadout(items=equipped)

    for it in loadout.items:
        passives = dict(it.get("passives") or {})
        passives["_upgrade"] = it.get("_upgrade", 0)
        _apply_passives(loadout, passives)
        if it.get("aura"):
            _apply_aura(loadout, it["aura"])

    # nation auras from other citizens' mythics
    if player.nation_id:
        await _apply_nation_auras(session, player, loadout)

    # ready charges
    for it in loadout.items:
        charge = it.get("charge")
        if not charge:
            continue
        if await _charge_ready(session, player.vk_id, it["id"], charge):
            loadout.charges_ready[charge["code"]] = it["id"]

    # caps on passives
    loadout.work_mult = min(config.WORK_MULT_CAP, max(-0.2, loadout.work_mult))
    loadout.raid_mult = min(config.RAID_MULT_CAP, max(-0.15, loadout.raid_mult))
    return loadout


def _apply_passives(loadout: Loadout, p: dict) -> None:
    upgrade = int(p.get("_upgrade") or 0)
    scale = 1.0 + config.UPGRADE_BONUS_PER_LEVEL * upgrade
    loadout.work_mult += float(p.get("work_mult") or 0) * scale
    loadout.raid_mult += float(p.get("raid_mult") or 0) * scale
    loadout.raid_defend += float(p.get("raid_defend") or 0) * scale
    loadout.raid_cd_hours += float(p.get("raid_cd_hours") or 0)
    loadout.raid_leader_share += float(p.get("raid_leader_share") or 0)
    loadout.tax_add += float(p.get("tax_add") or 0)
    loadout.smuggle_chance += float(p.get("smuggle_chance") or 0)
    loadout.smuggle_reward += float(p.get("smuggle_reward") or 0)
    loadout.smuggle_fine_mult *= float(p.get("smuggle_fine_mult") or 1.0)
    loadout.jail_hours_mult *= float(p.get("jail_hours_mult") or 1.0)
    loadout.treasury_bonus_add += int(p.get("treasury_bonus_add") or 0)
    loadout.loot_luck += float(p.get("loot_luck") or 0)
    for job, bonus in (p.get("job_bonus") or {}).items():
        loadout.job_bonus[job] = loadout.job_bonus.get(job, 0.0) + float(bonus)


def _apply_aura(loadout: Loadout, aura: dict) -> None:
    loadout.nation_work_mult += float(aura.get("nation_work_mult") or 0)
    loadout.nation_treasury_raid_defend += float(
        aura.get("nation_treasury_raid_defend") or 0
    )
    if aura.get("personal_gold_vein"):
        loadout.personal_gold_vein = True
    if aura.get("raid_target_mark"):
        loadout.raid_target_mark = True


async def _apply_nation_auras(
    session: AsyncSession, player: Player, loadout: Loadout
) -> None:
    """Ауры мификов граждан той же страны (кроме уже учтённых своих)."""
    from db.models import Player as P

    result = await session.execute(
        select(P.vk_id).where(P.nation_id == player.nation_id)
    )
    vk_ids = [r[0] for r in result.all()]
    if not vk_ids:
        return
    eq = await session.execute(
        select(EquippedItem).where(EquippedItem.player_vk_id.in_(vk_ids))
    )
    own_ids = {it["id"] for it in loadout.items}
    for row in eq.scalars().all():
        if row.item_id in own_ids and row.player_vk_id == player.vk_id:
            continue
        it = cat.get_item(row.item_id)
        if not it or not it.get("aura"):
            continue
        # nation-wide parts only (not personal_gold_vein for others)
        aura = it["aura"]
        loadout.nation_work_mult += float(aura.get("nation_work_mult") or 0)
        loadout.nation_treasury_raid_defend += float(
            aura.get("nation_treasury_raid_defend") or 0
        )
        if aura.get("raid_target_mark"):
            loadout.raid_target_mark = True


async def _charge_ready(
    session: AsyncSession, vk_id: int, item_id: str, charge: dict
) -> bool:
    result = await session.execute(
        select(ItemCharge).where(
            ItemCharge.player_vk_id == vk_id,
            ItemCharge.item_id == item_id,
        )
    )
    row = result.scalar_one_or_none()
    if not row or not row.last_used_at:
        return True
    last = ensure_aware(row.last_used_at)
    cd = timedelta(hours=float(charge.get("cooldown_hours") or 24))
    return utcnow() >= last + cd


async def try_consume_charge(
    session: AsyncSession, player: Player, code: str, loadout: Loadout | None = None
) -> str | None:
    """Списать заряд по коду. Вернуть имя предмета или None."""
    lo = loadout or await get_loadout(session, player)
    item_id = lo.charges_ready.get(code)
    if not item_id:
        return None
    it = cat.get_item(item_id)
    if not it or not it.get("charge"):
        return None
    result = await session.execute(
        select(ItemCharge).where(
            ItemCharge.player_vk_id == player.vk_id,
            ItemCharge.item_id == item_id,
        )
    )
    row = result.scalar_one_or_none()
    now = utcnow()
    if row:
        row.last_used_at = now
    else:
        session.add(
            ItemCharge(player_vk_id=player.vk_id, item_id=item_id, last_used_at=now)
        )
    await session.commit()
    return it["name"]


async def get_buff(session: AsyncSession, vk_id: int, code: str) -> PlayerBuff | None:
    result = await session.execute(
        select(PlayerBuff).where(
            PlayerBuff.player_vk_id == vk_id,
            PlayerBuff.buff_code == code,
        )
    )
    return result.scalar_one_or_none()


async def set_buff(
    session: AsyncSession, vk_id: int, code: str, stacks: int, meta: str = ""
) -> None:
    buff = await get_buff(session, vk_id, code)
    if buff:
        buff.stacks = stacks
        buff.meta = meta
    else:
        session.add(
            PlayerBuff(player_vk_id=vk_id, buff_code=code, stacks=stacks, meta=meta)
        )
    await session.commit()


async def consume_buff_stack(session: AsyncSession, vk_id: int, code: str) -> bool:
    buff = await get_buff(session, vk_id, code)
    if not buff or buff.stacks <= 0:
        return False
    buff.stacks -= 1
    if buff.stacks <= 0:
        await session.delete(buff)
    await session.commit()
    return True


def work_multiplier_from_loadout(loadout: Loadout, job: str) -> float:
    job_b = float(loadout.job_bonus.get(job, 0.0))
    total = 1.0 + loadout.work_mult + job_b + loadout.nation_work_mult
    # soft re-cap after job bonus
    bonus = total - 1.0
    bonus = min(config.WORK_MULT_CAP + 0.15, max(-0.25, bonus))  # slight room for job
    return 1.0 + bonus


def apply_work_modifiers(
    base_gross: int, loadout: Loadout, job: str
) -> tuple[int, float]:
    mult = work_multiplier_from_loadout(loadout, job)
    return max(1, int(base_gross * mult)), mult


def apply_raid_modifiers(stolen: int, loadout: Loadout) -> tuple[int, float]:
    mult = 1.0 + loadout.raid_mult
    bonus = mult - 1.0
    bonus = min(config.RAID_MULT_CAP, max(-0.15, bonus))
    mult = 1.0 + bonus
    return max(1, int(stolen * mult)), mult


def format_loadout_short(loadout: Loadout) -> str:
    if not loadout.items:
        return "пусто"
    return ", ".join(cat.format_item(it) for it in loadout.items)
