import random
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from bot import config
from db.models import Player
from services.achievements import grant_title
from services.item_effects import get_buff, get_loadout, set_buff, try_consume_charge
from services.loot import grant_drop
from services.player import ensure_aware, regenerate_energy, utcnow
from services.flash_events import get_flash_event
from services.world_events import (
    get_active_event,
    loot_multiplier,
    smuggle_multiplier,
    tax_modifier,
    work_multiplier,
)


class SmuggleError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def assert_not_jailed(player: Player) -> None:
    until = ensure_aware(player.jail_until)
    if until and utcnow() < until:
        left = int((until - utcnow()).total_seconds() / 60) + 1
        raise SmuggleError(
            f"Ты в тюрьме ещё ~{left} мин. Выкуп: 🔓 / 🏪 Лавка."
        )


async def do_smuggle(session: AsyncSession, player: Player) -> dict:
    regenerate_energy(player)
    assert_not_jailed(player)
    now = utcnow()
    last = ensure_aware(player.last_smuggle_at)
    if last:
        ready = last + timedelta(minutes=config.SMUGGLE_COOLDOWN_MIN)
        if now < ready:
            mins = int((ready - now).total_seconds() / 60) + 1
            raise SmuggleError(f"Контрабанда на КД ~{mins} мин.")

    if player.energy < 1:
        raise SmuggleError("Недостаточно энергии.")

    loadout = await get_loadout(session, player)
    ev = await get_active_event(session)
    flash = await get_flash_event(session)
    event_key = ev["key"] if ev else None
    if loadout.personal_gold_vein:
        event_key = "gold_vein"

    chance = config.SMUGGLE_SUCCESS_CHANCE + loadout.smuggle_chance
    sm_mult = smuggle_multiplier(ev, flash)
    if sm_mult != 1.0:
        chance = chance * sm_mult
    chance = max(0.05, min(0.85, chance))
    success = random.random() < chance
    player.energy -= 1
    player.last_smuggle_at = now
    player.energy_updated_at = now
    charge_notes: list[str] = []
    if flash:
        charge_notes.append(f"⚡ {flash['title']}")

    if success:
        base = random.randint(config.SMUGGLE_REWARD_MIN, config.SMUGGLE_REWARD_MAX)
        gross = int(
            base
            * work_multiplier(ev, flash)
            * 3
            * (1.0 + loadout.smuggle_reward)
            * sm_mult
        )
        tax = 0
        if player.nation:
            rate = (
                (player.nation.tax_rate or 0.1)
                + tax_modifier(ev, flash)
                + loadout.tax_add
            )
            rate = max(0.0, min(0.4, rate))
            tax = max(1, int(gross * rate))
            player.nation.treasury += tax
        net = gross - tax
        player.crowns += net
        title = await grant_title(session, player, "smuggler")

        # shadow stash streak
        buff = await get_buff(session, player.vk_id, "shadow_streak")
        streak = (buff.stacks if buff else 0) + 1
        await set_buff(session, player.vk_id, "shadow_streak", streak)
        if streak >= 3 and "shadow_stash" in loadout.charges_ready:
            name = await try_consume_charge(session, player, "shadow_stash", loadout)
            if name and player.nation:
                player.nation.treasury += 300
                await set_buff(session, player.vk_id, "shadow_streak", 0)
                charge_notes.append(f"⚡ {name}: +300 в казну")

        await session.commit()
        drop = await grant_drop(
            session,
            player,
            "smuggle",
            success=True,
            event_key=event_key,
            loot_luck=loadout.loot_luck,
            loot_mult=loot_multiplier(ev, flash),
        )
        return {
            "success": True,
            "gross": gross,
            "tax": tax,
            "net": net,
            "crowns": player.crowns,
            "title": title,
            "jailed": False,
            "drop": drop,
            "charge_notes": charge_notes,
        }

    await set_buff(session, player.vk_id, "shadow_streak", 0)
    no_jail = False
    if "smuggle_no_jail" in loadout.charges_ready:
        name = await try_consume_charge(session, player, "smuggle_no_jail", loadout)
        if name:
            no_jail = True
            charge_notes.append(f"⚡ {name}: без тюрьмы")

    jail_hours = config.SMUGGLE_JAIL_HOURS * loadout.jail_hours_mult
    if not no_jail:
        player.jail_until = now + timedelta(hours=jail_hours)
    fine = min(player.crowns, int(random.randint(30, 80) * loadout.smuggle_fine_mult))
    player.crowns -= fine
    await session.commit()
    drop = await grant_drop(
        session,
        player,
        "smuggle",
        success=False,
        event_key=event_key,
        loot_luck=loadout.loot_luck,
    )
    return {
        "success": False,
        "fine": fine,
        "crowns": player.crowns,
        "jailed": not no_jail,
        "jail_hours": jail_hours if not no_jail else 0,
        "drop": drop,
        "charge_notes": charge_notes,
    }
