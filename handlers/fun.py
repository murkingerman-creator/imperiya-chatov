import re

from vkbottle.bot import Bot, Message

from bot import config
from bot.keyboards import (
    auction_keyboard,
    chatwar_targets_keyboard,
    duel_accept_keyboard,
    duel_menu_keyboard,
    election_citizens_keyboard,
    emotions_keyboard,
    jobs_keyboard,
    main_keyboard,
    more_keyboard,
    number_keyboard,
    rps_keyboard,
)
from db.database import SessionLocal
from handlers.common import reply, reply_here, resolve_name
from handlers.rules import match_cmd, payload_cmd
from services.achievements import grant_title
from services.auction import AuctionError, get_active_auctions, place_bid
from services.chatwars import (
    ChatWarError,
    active_war_text,
    start_war,
)
from services.duels import (
    RPS_LABEL,
    cleanup_duel,
    create_duel,
    get_duel,
    number_winner,
    rps_winner,
)
from services.elections import ElectionError, cast_vote, election_status, finish_election
from services.notify import notify_nation_chat, post_wall
from services.player import get_or_create_player
from services.quests import claim_quest
from services.smuggle import SmuggleError, do_smuggle
from services.war import raid_candidates
from services.world_events import ensure_daily_event, format_event

CHATWAR_RE = re.compile(r"^(?:война\s+бесед|чатвар)\s+(.+)$", re.IGNORECASE)
BID_RE = re.compile(r"^(?:ставка|bid)\s+(\d+)\s+(\d+)$", re.IGNORECASE)

EMOTION_TEMPLATES = {
    "party": (
        "🎉 {flag} {name} объявляет всенародный праздник!\n"
        "Девиз: {motto}\n{extra}"
    ),
    "war": (
        "⚔ {flag} {name} бьёт в барабаны войны!\n"
        "Граждане — к оружию!\n{extra}"
    ),
    "anthem": "🎵 Гимн страны {flag} {name}:\n{anthem}",
    "sad": "😢 {flag} {name} объявляет траур.\n{extra}",
}


def _is_chatwar_text(message: Message) -> bool:
    return bool(CHATWAR_RE.match((message.text or "").strip()))


def _is_bid_text(message: Message) -> bool:
    return bool(BID_RE.match((message.text or "").strip()))


def register(bot: Bot) -> None:
    @bot.on.message(func=match_cmd("more", "ещё", "еще", "🎯 ещё", "🎯 еще"))
    async def more_menu(message: Message):
        async with SessionLocal() as session:
            ev = await ensure_daily_event(session)
            await session.commit()
        await reply(message, 
            f"🎯 Доп. меню\n{format_event(ev)}\n\n"
            "Ивент · квест · аукцион · выборы · война бесед",
            keyboard=more_keyboard().get_json(),
        )

    @bot.on.message(
        func=match_cmd("world_event", "ивент", "ивент дня", "🌤 ивент дня", "событие")
    )
    async def world_event_handler(message: Message):
        async with SessionLocal() as session:
            ev = await ensure_daily_event(session)
            await session.commit()
        await reply(message, 
            f"🌤 Ивент дня\n{format_event(ev)}",
            keyboard=more_keyboard().get_json(),
        )

    @bot.on.message(func=match_cmd("smuggle", "контрабанда", "🕶 контрабанда"))
    async def smuggle_handler(message: Message):
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            try:
                result = await do_smuggle(session, player)
            except SmuggleError as e:
                await reply(message, e.message, keyboard=jobs_keyboard().get_json())
                return

            if result["success"]:
                title_line = f"\n🏅 Титул: {result['title']}" if result.get("title") else ""
                tax_line = f"\nНалог: −{result['tax']}" if result["tax"] else ""
                drop = result.get("drop")
                drop_line = f"\n✨ Дроп: {drop['text']}" if drop else ""
                notes = result.get("charge_notes") or []
                notes_line = ("\n" + "\n".join(notes)) if notes else ""
                await reply(message, 
                    f"🕶 Контрабанда удалась! ×3\n"
                    f"+{result['gross']}{tax_line}\n"
                    f"На руки: +{result['net']}\n"
                    f"💰 {result['crowns']}{title_line}{drop_line}{notes_line}",
                    keyboard=jobs_keyboard().get_json(),
                )
            else:
                drop = result.get("drop")
                drop_line = f"\n✨ Дроп: {drop['text']}" if drop else ""
                notes = result.get("charge_notes") or []
                notes_line = ("\n" + "\n".join(notes)) if notes else ""
                jail_line = (
                    f" · тюрьма {result['jail_hours']}ч"
                    if result.get("jailed")
                    else " · без тюрьмы"
                )
                await reply(message, 
                    f"🚔 Поймали!\n"
                    f"Штраф −{result['fine']}{jail_line}\n"
                    f"💰 {result['crowns']}{drop_line}{notes_line}",
                    keyboard=main_keyboard().get_json(),
                )

    @bot.on.message(func=match_cmd("quest", "квест", "📦 квест", "сундук"))
    async def quest_handler(message: Message):
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            progress = player.quest_jobs or 0
            needed = config.QUEST_JOBS_NEEDED
            in_cycle = progress % needed
            completed = progress // needed
            claimed = player.quest_claimed or 0
            if completed > claimed:
                try:
                    result = await claim_quest(session, player)
                except ValueError as e:
                    await reply(message, str(e), keyboard=more_keyboard().get_json())
                    return
                title_line = f"\n🏅 {result['title']}" if result.get("title") else ""
                await reply(message, 
                    f"📦 Сундук квеста!\n+{result['reward']} крон\n"
                    f"💰 {result['crowns']}{title_line}",
                    keyboard=more_keyboard().get_json(),
                )
                return

            await reply(message, 
                f"📦 Квест: сделай {needed} работы → сундук\n"
                f"Прогресс: {in_cycle}/{needed} "
                f"(всего работ {progress}, сундуков {claimed})",
                keyboard=more_keyboard().get_json(),
            )

    @bot.on.message(func=match_cmd("emotions", "эмоции", "🎭 эмоции", "клан эмоции"))
    async def emotions_menu(message: Message):
        await reply(message, 
            "🎭 Эмоции страны — сообщение уйдёт в беседу государства.",
            keyboard=emotions_keyboard().get_json(),
        )

    @bot.on.message(func=payload_cmd("emo"))
    async def emotion_send(message: Message):
        payload = message.get_payload_json() or {}
        kind = str(payload.get("kind") or "")
        if kind not in EMOTION_TEMPLATES:
            await reply(message, "Неизвестная эмоция.", keyboard=emotions_keyboard().get_json())
            return
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            if not player.nation:
                await reply(message, "Нужна страна.", keyboard=main_keyboard().get_json())
                return
            from services.roles import can_herald

            if not await can_herald(session, player):
                await reply(
                    message,
                    "Эмоции шлёт лидер или глашатай.",
                    keyboard=main_keyboard().get_json(),
                )
                return
            n = player.nation
            extra = n.motto or n.laws or "Слава Империи чатов!"
            text = EMOTION_TEMPLATES[kind].format(
                flag=n.flag_emoji,
                name=n.name,
                motto=n.motto or "—",
                anthem=n.anthem or "(гимн ещё не написан)",
                extra=extra,
            )
            await notify_nation_chat(message.ctx_api, n.chat_peer_id, text)
            await reply(message, 
                f"Отправлено в беседу {n.flag_emoji} {n.name}.",
                keyboard=emotions_keyboard().get_json(),
            )

    @bot.on.message(func=match_cmd("duel_menu", "дуэль", "🎲 дуэль", "дуэли"))
    async def duel_menu(message: Message):
        await reply(message, 
            "🎲 Дуэль в беседе\n"
            f"Ставка {config.DUEL_MIN_BET}–{config.DUEL_MAX_BET} крон.\n"
            "КНБ или угадай число 1–5. Создай — соперник примет.",
            keyboard=duel_menu_keyboard().get_json(),
        )

    @bot.on.message(func=payload_cmd("duel_create"))
    async def duel_create(message: Message):
        payload = message.get_payload_json() or {}
        mode = str(payload.get("mode") or "rps")
        bet = int(payload.get("bet") or 50)
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            if player.crowns < bet:
                await reply(message, 
                    f"Не хватает крон (нужно {bet}).",
                    keyboard=duel_menu_keyboard().get_json(),
                )
                return
            try:
                duel = create_duel(message.peer_id, player.vk_id, player.name, bet, mode)
            except ValueError as e:
                await reply(message, str(e), keyboard=duel_menu_keyboard().get_json())
                return
            player.crowns -= bet
            await session.commit()

        mode_label = "камень-ножницы-бумага" if mode == "rps" else "угадай число"
        # inline в том же peer — соперник видит кнопку в беседе
        await reply_here(
            message,
            f"🎲 {name} вызывает на дуэль!\n"
            f"Режим: {mode_label} · ставка {bet}\n"
            f"Кто готов — жми «Принять» (код {duel.token}).",
            keyboard=duel_accept_keyboard(duel.token).get_json(),
        )

    @bot.on.message(func=payload_cmd("duel_accept"))
    async def duel_accept(message: Message):
        payload = message.get_payload_json() or {}
        token = str(payload.get("token") or "")
        duel = get_duel(token)
        if not duel:
            await reply(message, "Дуэль истекла или не найдена.", keyboard=main_keyboard().get_json())
            return
        if message.from_id == duel.challenger_id:
            await message.answer("Нельзя принять свою дуэль.")
            return
        if duel.opponent_id:
            await message.answer("Уже есть соперник.")
            return

        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            if player.crowns < duel.bet:
                await message.answer(f"Нужно {duel.bet} крон.")
                return
            player.crowns -= duel.bet
            await session.commit()

        duel.opponent_id = message.from_id
        kb = rps_keyboard(token) if duel.mode == "rps" else number_keyboard(token)
        prompt = (
            "Выберите ход (оба игрока):"
            if duel.mode == "rps"
            else "Угадайте число 1–5 (оба игрока):"
        )
        await reply_here(
            message,
            f"✅ {name} принял дуэль vs {duel.challenger_name}!\n{prompt}",
            keyboard=kb.get_json(),
        )

    @bot.on.message(func=payload_cmd("duel_move"))
    async def duel_move(message: Message):
        payload = message.get_payload_json() or {}
        token = str(payload.get("token") or "")
        move = str(payload.get("move") or "")
        duel = get_duel(token)
        if not duel or not duel.opponent_id:
            await reply(message, "Дуэль недоступна.", keyboard=main_keyboard().get_json())
            return
        if message.from_id not in (duel.challenger_id, duel.opponent_id):
            await message.answer("Ты не участник этой дуэли.")
            return

        if duel.mode == "rps" and move not in RPS_LABEL:
            await message.answer("Неверный ход.")
            return
        if duel.mode == "number" and move not in {"1", "2", "3", "4", "5"}:
            await message.answer("Число от 1 до 5.")
            return

        if message.from_id == duel.challenger_id:
            if duel.challenger_move:
                await message.answer("Ты уже сходил.")
                return
            duel.challenger_move = move
        else:
            if duel.opponent_move:
                await message.answer("Ты уже сходил.")
                return
            duel.opponent_move = move

        if not duel.challenger_move or not duel.opponent_move:
            await message.answer("Ход принят. Ждём второго игрока…")
            return

        await _resolve_duel(message, duel)

    @bot.on.message(func=match_cmd("auction", "аукцион", "🏷 аукцион", "трофей"))
    async def auction_menu(message: Message):
        async with SessionLocal() as session:
            auctions = await get_active_auctions(session)
            if not auctions:
                await reply(message, 
                    "🏷 Активных аукционов нет.\nТрофеи выпадают после рейдов.",
                    keyboard=more_keyboard().get_json(),
                )
                return
            lines = ["🏷 Аукцион трофеев (ставки — только лидеры):"]
            for a in auctions:
                lines.append(f"#{a.id} {a.item_name} — ставка {a.bid}")
            lines.append("\nКнопка или: ставка ID сумма")
            await reply(message, 
                "\n".join(lines),
                keyboard=auction_keyboard(auctions).get_json(),
            )

    @bot.on.message(func=payload_cmd("auction_bid"))
    async def auction_bid_payload(message: Message):
        payload = message.get_payload_json() or {}
        aid = int(payload.get("id") or 0)
        amount = int(payload.get("amount") or 0)
        await _do_bid(message, aid, amount)

    @bot.on.message(func=_is_bid_text)
    async def auction_bid_text(message: Message):
        m = BID_RE.match((message.text or "").strip())
        if m:
            await _do_bid(message, int(m.group(1)), int(m.group(2)))

    @bot.on.message(func=match_cmd("election", "выборы", "🗳 выборы"))
    async def election_menu(message: Message):
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            if not player.nation:
                await reply(message, "Нужна страна.", keyboard=more_keyboard().get_json())
                return
            status = await election_status(session, player.nation)
            from sqlalchemy import select
            from db.models import Player as P

            result = await session.execute(
                select(P).where(P.nation_id == player.nation_id).order_by(P.crowns.desc())
            )
            citizens = list(result.scalars().all())
            await reply(message, 
                f"🗳 Выборы лидера (раз в неделю)\n{status}\n\n"
                "Голос — кнопкой по кандидату. Завершить — когда ≥2 голосов.",
                keyboard=election_citizens_keyboard(citizens).get_json(),
            )

    @bot.on.message(func=payload_cmd("election_vote"))
    async def election_vote(message: Message):
        payload = message.get_payload_json() or {}
        cand = int(payload.get("vk_id") or 0)
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            try:
                await cast_vote(session, player, cand)
            except ElectionError as e:
                await reply(message, e.message, keyboard=more_keyboard().get_json())
                return
            status = await election_status(session, player.nation)
            await reply(message, f"✅ Голос учтён.\n{status}", keyboard=more_keyboard().get_json())

    @bot.on.message(func=payload_cmd("election_finish"))
    async def election_finish(message: Message):
        name = await resolve_name(message)
        async with SessionLocal() as session:
            player = await get_or_create_player(session, message.from_id, name)
            if not player.nation:
                await message.answer("Нужна страна.")
                return
            try:
                result = await finish_election(session, player.nation)
            except ElectionError as e:
                await reply(message, e.message, keyboard=more_keyboard().get_json())
                return
            w = result["winner"]
            title_line = f"\n🏅 {result['title']}" if result.get("title") else ""
            text = (
                f"🏁 Выборы завершены!\n"
                f"Новый лидер: {w.name} ({result['votes']}/{result['total']}){title_line}"
            )
            await notify_nation_chat(message.ctx_api, player.nation.chat_peer_id, text)
            await reply(message, text, keyboard=more_keyboard().get_json())

    @bot.on.message(func=match_cmd("chatwar", "война бесед", "⚔ война бесед", "чатвар"))
    async def chatwar_menu(message: Message):
        name = await resolve_name(message)
        async with SessionLocal() as session:
            status = await active_war_text(session)
            player = await get_or_create_player(session, message.from_id, name)
            if (
                not player.nation
                or player.nation.leader_id != player.vk_id
            ):
                await reply(message, 
                    f"{status}\n\nОбъявить может только лидер "
                    f"(ставка казны {config.CHAT_WAR_STAKE}).",
                    keyboard=more_keyboard().get_json(),
                )
                return
            targets = await raid_candidates(session, player.nation.id)
            await reply(message, 
                f"{status}\n\n⚔ Объяви войну бесед (банк {config.CHAT_WAR_STAKE * 2}).\n"
                "Очки — за успешные рейды. Или: война бесед Название",
                keyboard=chatwar_targets_keyboard([t.name for t in targets]).get_json(),
            )

    @bot.on.message(func=payload_cmd("chatwar_start"))
    async def chatwar_start_payload(message: Message):
        payload = message.get_payload_json() or {}
        target = str(payload.get("target") or "").strip()
        if target:
            await _start_chatwar(message, target)

    @bot.on.message(func=_is_chatwar_text)
    async def chatwar_start_text(message: Message):
        m = CHATWAR_RE.match((message.text or "").strip())
        if m:
            await _start_chatwar(message, m.group(1).strip())


async def _do_bid(message: Message, auction_id: int, amount: int) -> None:
    name = await resolve_name(message)
    async with SessionLocal() as session:
        player = await get_or_create_player(session, message.from_id, name)
        try:
            auction = await place_bid(session, auction_id, player, amount)
        except AuctionError as e:
            await reply(message, e.message, keyboard=more_keyboard().get_json())
            return
        await reply(message, 
            f"🏷 Ставка принята: #{auction.id} {auction.item_name} → {auction.bid}",
            keyboard=more_keyboard().get_json(),
        )


async def _start_chatwar(message: Message, target: str) -> None:
    name = await resolve_name(message)
    async with SessionLocal() as session:
        player = await get_or_create_player(session, message.from_id, name)
        if not player.nation or player.nation.leader_id != player.vk_id:
            await message.answer("Только лидер объявляет войну бесед.")
            return
        try:
            war = await start_war(session, player.nation, target)
        except ChatWarError as e:
            await reply(message, e.message, keyboard=more_keyboard().get_json())
            return
        from services.nation import get_nation_by_id

        a = player.nation
        b = await get_nation_by_id(session, war.nation_b_id)
        announce = (
            f"⚔ ВОЙНА БЕСЕД!\n"
            f"{a.flag_emoji} {a.name} vs {b.flag_emoji if b else '?'} {b.name if b else '?'}\n"
            f"Банк {war.stake * 2} · {config.CHAT_WAR_HOURS}ч · очки за рейды"
        )
        await post_wall(message.ctx_api, announce)
        await notify_nation_chat(message.ctx_api, a.chat_peer_id, announce)
        if b:
            await notify_nation_chat(message.ctx_api, b.chat_peer_id, announce)
        await reply(message, announce, keyboard=more_keyboard().get_json())


async def _resolve_duel(message: Message, duel) -> None:
    pot = duel.bet * 2
    if duel.mode == "rps":
        winner = rps_winner(duel.challenger_move, duel.opponent_move)
        detail = (
            f"{RPS_LABEL.get(duel.challenger_move)} vs "
            f"{RPS_LABEL.get(duel.opponent_move)}"
        )
    else:
        a = int(duel.challenger_move)
        b = int(duel.opponent_move)
        winner = number_winner(a, b, duel.secret_number or 3)
        detail = f"загадано {duel.secret_number}: {a} vs {b}"

    async with SessionLocal() as session:
        ch = await get_or_create_player(session, duel.challenger_id, duel.challenger_name)
        op = await get_or_create_player(session, duel.opponent_id, "Соперник")
        title_line = ""
        if winner == 0:
            ch.crowns += duel.bet
            op.crowns += duel.bet
            text = f"🤝 Ничья! ({detail})\nСтавки возвращены."
        elif winner == 1:
            ch.crowns += pot
            t = await grant_title(session, ch, "duelist")
            if t:
                title_line = f"\n🏅 {t}"
            text = (
                f"🏆 Победа {ch.name}! ({detail})\n"
                f"+{pot} крон{title_line}"
            )
        else:
            op.crowns += pot
            t = await grant_title(session, op, "duelist")
            if t:
                title_line = f"\n🏅 {t}"
            text = (
                f"🏆 Победа {op.name}! ({detail})\n"
                f"+{pot} крон{title_line}"
            )
        await session.commit()

    cleanup_duel(duel.token)
    await reply_here(message, text)
