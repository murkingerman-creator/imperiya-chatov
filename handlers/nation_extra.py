"""UI: казна, щит, цели недели, роли, сезон."""

from vkbottle import Keyboard, KeyboardButtonColor, Text
from vkbottle.bot import Bot, Message

from bot import config
from bot.keyboards import (
    main_keyboard,
    roles_assign_keyboard,
    roles_keyboard,
    treasury_keyboard,
)
from db.database import SessionLocal
from handlers.common import reply, resolve_name
from handlers.rules import match_cmd, payload_cmd
from services.announce import announce_nation
from services.nation import list_citizens
from services.player import ensure_aware, get_or_create_player, utcnow
from services.roles import RolesError, clear_role, get_role, set_role
from services.season import current_season_id, top_seasons
from services.treasury import (
    TreasuryError,
    activate_shield,
    amnesty,
    buy_shield_pool,
    contribute_shield,
    feast,
    fortify,
    payout,
    raise_monument,
    raid_fund,
    scholarship,
    treasury_catalog_text,
    war_levy,
    work_edict,
)
from services.weeklies import WeeklyError, claim_weekly, ensure_weekly, status_text


def register(bot: Bot) -> None:
    @bot.on.message(func=match_cmd("treasury", "казна", "🏛 казна"))
    async def treasury_menu(message: Message):
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            if not player.nation:
                await reply(
                    message,
                    "Нужна страна.",
                    keyboard=main_keyboard().get_json(),
                )
                return
            n = player.nation
            from services.player import ensure_aware, utcnow

            shield = ""
            until = ensure_aware(n.shield_until)
            if until and until > utcnow():
                left = int((until - utcnow()).total_seconds() / 3600) + 1
                shield = f"\n🛡 Щит активен ~{left}ч"
            work = ""
            wu = ensure_aware(n.work_buff_until)
            if wu and wu > utcnow():
                work = f"\n⚒ Указ о труде до {wu.strftime('%H:%M')} UTC"
            await reply(
                message,
                treasury_catalog_text(n) + "\n\nГраждане: взнос в щит личными кронами.",
                keyboard=treasury_keyboard().get_json(),
            )

    @bot.on.message(func=payload_cmd("tr_spend"))
    async def treasury_spend(message: Message):
        payload = message.get_payload_json() or {}
        action = str(payload.get("action") or "")
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            try:
                if action == "work":
                    r = await work_edict(session, player)
                    text = f"⚒ Указ о труде (−{r['cost']} казны). +10% к работам 6ч."
                elif action == "levy":
                    r = await war_levy(session, player)
                    text = (
                        f"⚔ Военный сбор (−{r['cost']}). "
                        f"+{r['bonus_pct']}% к твоему следующему рейду."
                    )
                elif action == "payout":
                    r = await payout(session, player)
                    text = (
                        f"💰 Раздача (−{r['cost']}): "
                        f"+{r['share']} ×{r['citizens']} гражданам."
                    )
                elif action == "amnesty":
                    r = await amnesty(session, player)
                    text = f"🕊 Амнистия (−{r['cost']}): освобождено {r['freed']}."
                elif action == "shield_on":
                    r = await activate_shield(session, player)
                    text = f"🛡 Щит на 24ч! Фонд остаток: {r['pool']}."
                elif action == "shield_pay":
                    r = await contribute_shield(session, player)
                    text = (
                        f"🛡 Взнос {r['cost']}. Фонд щита: "
                        f"{r['pool']}/{config.NATION_SHIELD_POOL_NEED}."
                    )
                elif action == "feast":
                    r = await feast(session, player)
                    text = (
                        f"🎉 Праздник (−{r['cost']}): +энергия {r['boosted']} гражданам, "
                        f"работы +10% на {r['hours']}ч."
                    )
                elif action == "fortify":
                    r = await fortify(session, player)
                    text = (
                        f"🧱 Укрепление (−{r['cost']}): защита казны "
                        f"+{r['defend_pct']}% на {r['hours']}ч."
                    )
                elif action == "scholar":
                    r = await scholarship(session, player)
                    text = (
                        f"📚 Стипендия (−{r['cost']}): XP граждан ×{r['mult']} "
                        f"на {r['hours']}ч."
                    )
                elif action == "raid_fund":
                    r = await raid_fund(session, player)
                    text = (
                        f"⚔ Фонд рейда (−{r['cost']}): заряд ×{r['charges']}, "
                        f"следующий рейд +{r['steal_pct']}% добычи."
                    )
                elif action == "buy_shield":
                    r = await buy_shield_pool(session, player)
                    text = (
                        f"🛡 Из казны в фонд щита: −{r['cost']} → +{r['added']}. "
                        f"Фонд: {r['pool']}/{config.NATION_SHIELD_POOL_NEED}."
                    )
                elif action == "monument":
                    r = await raise_monument(session, player)
                    text = (
                        f"🗿 Монумент ур.{r['level']} (−{r['cost']})! "
                        f"Постоянно +{r['work_pct']}% к работам страны."
                    )
                else:
                    await reply(message, "Неизвестно.", keyboard=treasury_keyboard().get_json())
                    return
            except TreasuryError as e:
                await reply(message, e.message, keyboard=treasury_keyboard().get_json())
                return
            await announce_nation(message.ctx_api, player.nation, text)
            await reply(message, text, keyboard=treasury_keyboard().get_json())

    @bot.on.message(func=match_cmd("weekly", "цель недели", "📅 цель", "цель"))
    async def weekly_menu(message: Message):
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            if not player.nation:
                await reply(message, "Нужна страна.", keyboard=main_keyboard().get_json())
                return
            w = await ensure_weekly(session, player.nation)
            await session.commit()
            kb = Keyboard(one_time=False, inline=False)
            if (
                player.nation.leader_id == player.vk_id
                and w.progress >= w.target
                and not w.claimed
            ):
                kb.add(
                    Text("🎁 Забрать награду", {"cmd": "weekly_claim"}),
                    color=KeyboardButtonColor.POSITIVE,
                )
                kb.row()
            kb.add(Text("📋 Меню", {"cmd": "menu"}), color=KeyboardButtonColor.SECONDARY)
            await reply(message, status_text(w), keyboard=kb.get_json())

    @bot.on.message(func=payload_cmd("weekly_claim"))
    async def weekly_claim(message: Message):
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            try:
                r = await claim_weekly(session, player)
            except WeeklyError as e:
                await reply(message, e.message, keyboard=main_keyboard().get_json())
                return
            text = f"📅 Цель недели! Казна +{r.get('reward', config.WEEKLY_REWARD_TREASURY)}"
            await announce_nation(message.ctx_api, player.nation, text)
            await reply(message, text, keyboard=main_keyboard().get_json())

    @bot.on.message(func=match_cmd("roles", "роли", "👑 роли", "офицеры"))
    async def roles_menu(message: Message):
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            if not player.nation or player.nation.leader_id != player.vk_id:
                await reply(
                    message,
                    "Роли выдаёт только лидер.",
                    keyboard=main_keyboard().get_json(),
                )
                return
            lines = ["👑 Роли страны", "⚔ Воевода — рейды", "💰 Казначей — казна", "📢 Глашатай — эмоции"]
            for role, label in (
                ("warlord", "Воевода"),
                ("treasurer", "Казначей"),
                ("herald", "Глашатай"),
            ):
                from services.roles import get_role

                row = await get_role(session, player.nation_id, role)
                who = "—"
                if row:
                    from sqlalchemy import select
                    from db.models import Player as P

                    res = await session.execute(select(P).where(P.vk_id == row.vk_id))
                    p = res.scalar_one_or_none()
                    who = p.name if p else str(row.vk_id)
                lines.append(f"{label}: {who}")
            await reply(message, "\n".join(lines), keyboard=roles_keyboard().get_json())

    @bot.on.message(func=payload_cmd("role_pick"))
    async def role_pick(message: Message):
        payload = message.get_payload_json() or {}
        role = str(payload.get("role") or "")
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            if not player.nation or player.nation.leader_id != player.vk_id:
                return
            if payload.get("clear"):
                try:
                    msg = await clear_role(session, player, role)
                except RolesError as e:
                    await reply(message, e.message, keyboard=roles_keyboard().get_json())
                    return
                await reply(message, msg, keyboard=roles_keyboard().get_json())
                return
            citizens = [
                c
                for c in await list_citizens(session, player.nation.id, 10)
                if c.vk_id != player.vk_id
            ]
            await reply(
                message,
                f"Кому дать роль {role}?",
                keyboard=roles_assign_keyboard(role, citizens).get_json(),
            )

    @bot.on.message(func=payload_cmd("role_set"))
    async def role_set(message: Message):
        payload = message.get_payload_json() or {}
        role = str(payload.get("role") or "")
        vk_id = int(payload.get("vk_id") or 0)
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            try:
                msg = await set_role(session, player, vk_id, role)
            except RolesError as e:
                await reply(message, e.message, keyboard=roles_keyboard().get_json())
                return
            await announce_nation(message.ctx_api, player.nation, msg)
            await reply(message, msg, keyboard=roles_keyboard().get_json())

    @bot.on.message(func=match_cmd("season", "сезон", "🏆 сезон"))
    async def season_menu(message: Message):
        async with SessionLocal() as session:
            rows = await top_seasons(session, 10)
            sid = current_season_id()
            lines = [f"🏆 Сезон {sid}", "Очки: рейд +2 / отбитие +1 / война бесед +5", ""]
            if not rows:
                lines.append("Пока пусто — воюйте!")
            for i, (sc, nation) in enumerate(rows, 1):
                lines.append(
                    f"{i}. {nation.flag_emoji} {nation.name} — {sc.points}"
                )
            await reply(message, "\n".join(lines), keyboard=main_keyboard().get_json())
