import re

from vkbottle.bot import Bot, Message

from bot.keyboards import main_keyboard, raid_targets_keyboard
from db.database import SessionLocal
from handlers.common import resolve_name
from handlers.rules import match_cmd, payload_cmd
from services.chronicle_store import add_event
from services.notify import notify_nation_chat
from services.player import get_or_create_player
from services.war import WarError, raid, raid_candidates

RAID_RE = re.compile(r"^(?:⚔|рейд)\s+(.+)$", re.IGNORECASE)


def _is_raid_text(message: Message) -> bool:
    return bool(RAID_RE.match((message.text or "").strip()))


def register(bot: Bot) -> None:
    @bot.on.message(func=match_cmd("war", "война", "⚔ война", "рейд", "⚔ рейд"))
    async def war_menu(message: Message):
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)

            if not player.nation:
                await message.answer(
                    "Сначала вступи в страну или оснуй её.",
                    keyboard=main_keyboard().get_json(),
                )
                return

            if player.nation.leader_id != player.vk_id:
                await message.answer(
                    f"Рейды объявляет только лидер.\n"
                    f"Твоя страна: {player.nation.flag_emoji} {player.nation.name}\n"
                    f"Казна: {player.nation.treasury}",
                    keyboard=main_keyboard().get_json(),
                )
                return

            targets = await raid_candidates(session, player.nation.id)
            if not targets:
                await message.answer(
                    "Нет богатых целей. Пусть у стран наполнится казна.",
                    keyboard=main_keyboard().get_json(),
                )
                return

            lines = [
                f"⚔ Рейд от {player.nation.flag_emoji} {player.nation.name}",
                "Цель кнопкой или: рейд Название",
                "",
            ]
            for t in targets:
                lines.append(f"• {t.flag_emoji} {t.name} — казна {t.treasury}")

            await message.answer(
                "\n".join(lines),
                keyboard=raid_targets_keyboard([t.name for t in targets]).get_json(),
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
            await message.answer(e.message, keyboard=main_keyboard().get_json())
            return

        atk = result["attacker"]
        dfn = result["defender"]
        extra = ""
        if result.get("titles"):
            extra += f"\n🏅 {', '.join(result['titles'])}"
        trophy = result.get("trophy")
        if trophy:
            extra += (
                f"\n🏷 Трофей на аукционе: {trophy.item_name} "
                f"(#{trophy.id}, старт {trophy.bid})"
            )
        text = (
            f"⚔ Рейд!\n"
            f"{atk.flag_emoji} {atk.name} → {dfn.flag_emoji} {dfn.name}\n"
            f"Захвачено: {result['stolen']}\n"
            f"В казну: +{result['treasury_cut']} · Лидеру: +{result['leader_cut']}"
            f"{extra}"
        )
        await add_event(
            session,
            "raid",
            f"Рейд {atk.flag_emoji} {atk.name} на {dfn.flag_emoji} {dfn.name} (−{result['stolen']})",
            f"{atk.id},{dfn.id}",
        )
        await notify_nation_chat(
            message.ctx_api,
            atk.chat_peer_id,
            f"⚔ Победа! Рейд на {dfn.flag_emoji} {dfn.name}: +{result['stolen']} к казне/лидеру",
        )
        await notify_nation_chat(
            message.ctx_api,
            dfn.chat_peer_id,
            f"💥 Нас ограбили! {atk.flag_emoji} {atk.name} унесли {result['stolen']} из казны",
        )
        await message.answer(text, keyboard=main_keyboard().get_json())
