import re

from vkbottle.bot import Bot, Message

from bot.keyboards import main_keyboard, raid_targets_keyboard
from db.database import SessionLocal
from handlers.common import resolve_name
from handlers.rules import match_cmd, payload_cmd
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
                    "Пока нет богатых целей для рейда. "
                    "Подожди, пока у стран наполнится казна.",
                    keyboard=main_keyboard().get_json(),
                )
                return

            lines = [
                f"⚔ Рейд от имени {player.nation.flag_emoji} {player.nation.name}",
                "Выбери цель кнопкой или напиши: рейд Название",
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
        if not target:
            return
        await _do_raid(message, target)

    @bot.on.message(func=_is_raid_text)
    async def raid_by_text(message: Message):
        match = RAID_RE.match((message.text or "").strip())
        if not match:
            return
        target = match.group(1).strip()
        if not target:
            return
        await _do_raid(message, target)


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
        await message.answer(
            f"⚔ Рейд успешен!\n"
            f"{atk.flag_emoji} {atk.name} → {dfn.flag_emoji} {dfn.name}\n"
            f"Захвачено: {result['stolen']} крон\n"
            f"В казну: +{result['treasury_cut']}\n"
            f"Лидеру: +{result['leader_cut']} (баланс {result['leader_crowns']})\n"
            f"Казна цели теперь: {dfn.treasury}",
            keyboard=main_keyboard().get_json(),
        )
