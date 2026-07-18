import re

from vkbottle.bot import Bot, Message

from bot import config
from bot.keyboards import main_keyboard, war_actions_keyboard
from db.database import SessionLocal
from handlers.common import reply, resolve_name
from handlers.rules import match_cmd, payload_cmd
from services.chronicle import post_flash
from services.chronicle_store import add_event
from services.muster import MusterError, join_muster, open_muster
from services.notify import notify_nation_chat
from services.player import get_or_create_player
from services.roles import can_raid
from services.war import (
    WarError,
    nation_manpower,
    preview_raid_odds,
    raid,
    raid_candidates,
)

RAID_RE = re.compile(r"^(?:⚔|рейд)\s+(.+)$", re.IGNORECASE)

# Текст кнопки «⚔ …» не должен считаться командой рейда, если есть payload
_RAID_TEXT_BLOCKLIST = {
    "сбор",
    "указ",
    "раздача",
    "амнистия",
}


def _is_raid_text(message: Message) -> bool:
    payload = message.get_payload_json() or {}
    if isinstance(payload, dict) and payload.get("cmd"):
        return False
    text = (message.text or "").strip()
    m = RAID_RE.match(text)
    if not m:
        return False
    target = m.group(1).strip().casefold()
    if target in _RAID_TEXT_BLOCKLIST:
        return False
    return True


def _battle_line(result: dict) -> str:
    atk_m = result.get("atk_manpower") or {}
    def_m = result.get("def_manpower") or {}
    ally = result.get("ally")
    ally_m = result.get("ally_manpower") or {}
    ally_bit = ""
    if ally:
        ally_bit = (
            f" +🤝{ally.flag_emoji}{ally.name}"
            f"(👥{ally_m.get('total', '?')}/{ally_m.get('active', '?')})"
        )
    return (
        f"⚔ Сила: {result['atk_power']} "
        f"(👥{atk_m.get('total', result.get('atk_citizens', '?'))}"
        f"/{atk_m.get('active', '?')} акт.{ally_bit}) "
        f"vs {result['def_power']} "
        f"(👥{def_m.get('total', result.get('def_citizens', '?'))}"
        f"/{def_m.get('active', '?')} акт.)\n"
        f"Шанс успеха был {int(result['chance'] * 100)}%"
    )


def register(bot: Bot) -> None:
    @bot.on.message(func=match_cmd("war", "война", "⚔ война", "рейд", "⚔ рейд"))
    async def war_menu(message: Message):
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)

            if not player.nation:
                await reply(
                    message,
                    "Сначала вступи в страну или оснуй её.",
                    keyboard=main_keyboard().get_json(),
                )
                return

            if not await can_raid(session, player):
                await reply(
                    message,
                    f"Рейды — лидер или воевода.\n"
                    f"Твоя страна: {player.nation.flag_emoji} {player.nation.name}\n"
                    f"Казна: {player.nation.treasury}",
                    keyboard=main_keyboard().get_json(),
                )
                return

            targets = await raid_candidates(session, player.nation.id)
            if not targets:
                await reply(
                    message,
                    "Нет богатых целей. Пусть у стран наполнится казна.",
                    keyboard=main_keyboard().get_json(),
                )
                return

            my = await nation_manpower(session, player.nation.id)
            lines = [
                f"⚔ Рейд от {player.nation.flag_emoji} {player.nation.name}",
                f"👥 {my['total']} (активны {my['active']} за 48ч)",
                "📣 Сначала «Сбор» — граждане жмут «В строй» → больше силы.",
                "Сила: активные + экип + казарма + союз + сбор.",
                "Цель кнопкой или: рейд Название",
                "",
            ]
            for t in targets:
                odds = await preview_raid_odds(session, player.nation, t, player)
                dm = odds["defender_manpower"]
                shield = " 🛡" if odds["shielded"] else ""
                ally = odds.get("ally")
                ally_mark = f" ·🤝{ally.name}" if ally else ""
                muster = odds.get("muster") or 0
                muster_mark = f" ·📣{muster}" if muster else ""
                lines.append(
                    f"• {t.flag_emoji} {t.name} — казна {t.treasury} · "
                    f"👥{dm['total']}/{dm['active']}акт · "
                    f"~{int(odds['chance'] * 100)}%{shield}{ally_mark}{muster_mark}"
                )

            await reply(
                message,
                "\n".join(lines),
                keyboard=war_actions_keyboard([t.name for t in targets]).get_json(),
            )

    @bot.on.message(func=payload_cmd("muster_open"))
    async def muster_open_handler(message: Message):
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            try:
                r = await open_muster(session, player)
            except MusterError as e:
                await reply(message, e.message, keyboard=main_keyboard().get_json())
                return
            n = r["nation"]
            msg = (
                f"📣 Сбор объявлен в {n.flag_emoji} {n.name}!\n"
                f"Граждане: «В строй» (~{config.MUSTER_DURATION_MINUTES} мин).\n"
                f"Чем больше в строю — тем сильнее рейд."
            )
            await reply(message, msg, keyboard=main_keyboard().get_json())
            await notify_nation_chat(message.ctx_api, n.chat_peer_id, msg)

    @bot.on.message(func=payload_cmd("muster_join"))
    async def muster_join_handler(message: Message):
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            try:
                r = await join_muster(session, player)
            except MusterError as e:
                await reply(message, e.message, keyboard=main_keyboard().get_json())
                return
            await reply(
                message,
                f"✋ Ты в строю! Сейчас {r['joined']} чел. "
                f"Ждём рейда от лидера/воеводы.",
                keyboard=main_keyboard().get_json(),
            )

    @bot.on.message(func=payload_cmd("raid"))
    async def raid_by_payload(message: Message):
        payload = message.get_payload_json() or {}
        target = str(payload.get("target") or "").strip()
        if target:
            await _do_raid(message, target)

    @bot.on.message(func=_is_raid_text)
    async def raid_by_text(message: Message):
        match = RAID_RE.match((message.text or "").strip())
        if match:
            await _do_raid(message, match.group(1).strip())


async def _do_raid(message: Message, target: str) -> None:
    name = await resolve_name(message)
    async with SessionLocal() as session:
        player = await get_or_create_player(session, message.from_id, name)
        try:
            result = await raid(session, player, target)
        except WarError as e:
            await reply(message, e.message, keyboard=main_keyboard().get_json())
            return

        atk = result["attacker"]
        dfn = result["defender"]
        battle = _battle_line(result)

        if not result.get("success", True):
            text = (
                f"🛡 Рейд отбит!\n"
                f"{atk.flag_emoji} {atk.name} → {dfn.flag_emoji} {dfn.name}\n"
                f"{battle}\n"
                f"Оборона устояла. КД рейда сгорел."
            )
            notes = result.get("charge_notes") or []
            if notes:
                text += "\n" + "\n".join(notes)
            await notify_nation_chat(
                message.ctx_api,
                atk.chat_peer_id,
                f"🛡 Рейд на {dfn.flag_emoji} {dfn.name} отбит.\n{battle}",
            )
            await notify_nation_chat(
                message.ctx_api,
                dfn.chat_peer_id,
                f"🛡 Отразили рейд {atk.flag_emoji} {atk.name}!\n{battle}",
            )
            await reply(message, text, keyboard=main_keyboard().get_json())
            return

        extra = ""
        if result.get("titles"):
            extra += f"\n🏅 {', '.join(result['titles'])}"
        trophy = result.get("trophy")
        if trophy:
            extra += (
                f"\n🏷 Трофей на аукционе: {trophy.item_name} "
                f"(#{trophy.id}, старт {trophy.bid})"
            )
        drop = result.get("drop")
        if drop:
            extra += f"\n✨ Дроп: {drop['text']}"
        notes = result.get("charge_notes") or []
        if notes:
            extra += "\n" + "\n".join(notes)
        if result.get("reflected"):
            extra += f"\n🛡 Отражено защитой: {result['reflected']}"
        ally = result.get("ally")
        ally_cut = int(result.get("ally_cut") or 0)
        loot_line = (
            f"В казну: +{result['treasury_cut']} · Лидеру: +{result['leader_cut']}"
        )
        if ally and ally_cut:
            loot_line += f" · Союзу {ally.name}: +{ally_cut}"
        text = (
            f"⚔ Рейд удался!\n"
            f"{atk.flag_emoji} {atk.name} → {dfn.flag_emoji} {dfn.name}\n"
            f"{battle}\n"
            f"Захвачено: {result['stolen']}\n"
            f"{loot_line}"
            f"{extra}"
        )
        await add_event(
            session,
            "raid",
            f"{atk.flag_emoji} {atk.name} → {dfn.flag_emoji} {dfn.name} (−{result['stolen']} крон)",
            f"{atk.id},{dfn.id}",
        )
        from bot import config

        if result["stolen"] >= config.WALL_FLASH_RAID_MIN_STEAL:
            await post_flash(
                message.ctx_api,
                session,
                f"⚔ {atk.flag_emoji} {atk.name} ограбили "
                f"{dfn.flag_emoji} {dfn.name} на {result['stolen']}!",
            )
        await notify_nation_chat(
            message.ctx_api,
            atk.chat_peer_id,
            f"⚔ Победа! Рейд на {dfn.flag_emoji} {dfn.name}: +{result['stolen']}\n{battle}",
        )
        await notify_nation_chat(
            message.ctx_api,
            dfn.chat_peer_id,
            f"💥 Нас ограбили! {atk.flag_emoji} {atk.name} унесли {result['stolen']}\n{battle}",
        )
        ally = result.get("ally")
        ally_cut = int(result.get("ally_cut") or 0)
        if ally and ally_cut and ally.chat_peer_id:
            await notify_nation_chat(
                message.ctx_api,
                ally.chat_peer_id,
                f"🤝 Союзный рейд! {atk.flag_emoji} {atk.name} → "
                f"{dfn.flag_emoji} {dfn.name}\n"
                f"В вашу казну: +{ally_cut}",
            )
        await reply(message, text, keyboard=main_keyboard().get_json())
