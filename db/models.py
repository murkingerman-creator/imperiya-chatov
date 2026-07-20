from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Nation(Base):
    __tablename__ = "nations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_peer_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(64))
    flag_emoji: Mapped[str] = mapped_column(String(16), default="🏛")
    emblem_emoji: Mapped[str] = mapped_column(String(16), default="⚔️")
    motto: Mapped[str] = mapped_column(String(120), default="")
    capital: Mapped[str] = mapped_column(String(64), default="")
    government: Mapped[str] = mapped_column(String(32), default="республика")
    color_tag: Mapped[str] = mapped_column(String(32), default="лазурь")
    anthem: Mapped[str] = mapped_column(String(120), default="")
    laws: Mapped[str] = mapped_column(String(200), default="")
    welcome: Mapped[str] = mapped_column(String(120), default="")
    tax_rate: Mapped[float] = mapped_column(Float, default=0.10)
    leader_id: Mapped[int] = mapped_column(BigInteger, index=True)
    treasury: Mapped[int] = mapped_column(Integer, default=0)
    last_raid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    customized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    election_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    shield_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    shield_pool: Mapped[int] = mapped_column(Integer, default=0)
    work_buff_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # районы столицы 0..3
    district_market: Mapped[int] = mapped_column(Integer, default=0)
    district_barracks: Mapped[int] = mapped_column(Integer, default=0)
    district_temple: Mapped[int] = mapped_column(Integer, default=0)
    alliance_cd_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    muster_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # континент: north | south | center
    continent: Mapped[str] = mapped_column(String(16), default="center")
    discontent: Mapped[int] = mapped_column(Integer, default=0)
    # осада
    siege_target_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    siege_progress: Mapped[int] = mapped_column(Integer, default=0)
    siege_attempts: Mapped[int] = mapped_column(Integer, default=0)
    siege_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # реликвия нации (aura key)
    nation_relic: Mapped[str] = mapped_column(String(64), default="")
    monument_level: Mapped[int] = mapped_column(Integer, default=0)
    feast_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fortify_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    xp_buff_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    raid_fund: Mapped[int] = mapped_column(Integer, default=0)  # заряды на следующий рейд
    caravan_progress: Mapped[int] = mapped_column(Integer, default=0)
    caravan_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    players: Mapped[list["Player"]] = relationship(back_populates="nation")


class Player(Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    vk_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128), default="")
    crowns: Mapped[int] = mapped_column(Integer, default=100)
    energy: Mapped[int] = mapped_column(Integer, default=5)
    energy_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    nation_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("nations.id"), nullable=True, index=True
    )
    last_work_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_mine_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_market_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_guard_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_fish_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_farm_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_forge_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_tavern_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_stable_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_smuggle_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    daily_streak: Mapped[int] = mapped_column(Integer, default=0)
    last_daily_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    nation_left_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    invite_code: Mapped[str] = mapped_column(String(16), default="", index=True)
    referred_by_vk_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    jail_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    titles: Mapped[str] = mapped_column(String(512), default="")  # comma-separated codes
    quest_jobs: Mapped[int] = mapped_column(Integer, default=0)
    quest_claimed: Mapped[int] = mapped_column(Integer, default=0)
    raid_wins: Mapped[int] = mapped_column(Integer, default=0)
    onboarding_step: Mapped[int] = mapped_column(Integer, default=0)  # 0=done, 1..3=steps
    last_chat_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # можно ли писать в ЛС (False после VK 901/902; True после ответа игрока)
    dm_ok: Mapped[bool] = mapped_column(Boolean, default=True)
    saga_day: Mapped[int] = mapped_column(Integer, default=0)
    saga_claimed_day: Mapped[int] = mapped_column(Integer, default=0)
    last_protest_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    xp: Mapped[int] = mapped_column(Integer, default=0)
    level: Mapped[int] = mapped_column(Integer, default=1)
    last_wheel_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # mine=12,fish=3 — счётчики для рангов профессий
    job_counts: Mapped[str] = mapped_column(String(512), default="")
    tax_paid_week: Mapped[int] = mapped_column(Integer, default=0)
    tax_week_key: Mapped[str] = mapped_column(String(16), default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    nation: Mapped[Nation | None] = relationship(back_populates="players")


class WarLog(Base):
    __tablename__ = "war_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    attacker_nation_id: Mapped[int] = mapped_column(Integer, ForeignKey("nations.id"))
    defender_nation_id: Mapped[int] = mapped_column(Integer, ForeignKey("nations.id"))
    amount: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class ChronicleEvent(Base):
    __tablename__ = "chronicle_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(32), default="info")
    text: Mapped[str] = mapped_column(Text, default="")
    nation_ids: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class InviteUse(Base):
    __tablename__ = "invite_uses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    inviter_vk_id: Mapped[int] = mapped_column(BigInteger, index=True)
    invitee_vk_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    nation_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reward_paid: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class MetaKV(Base):
    __tablename__ = "meta_kv"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(String(512), default="")


class TrophyAuction(Base):
    __tablename__ = "trophy_auctions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    item_name: Mapped[str] = mapped_column(String(64))
    seller_nation_id: Mapped[int] = mapped_column(Integer)
    bid: Mapped[int] = mapped_column(Integer, default=0)
    bidder_vk_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    bidder_nation_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class ElectionVote(Base):
    __tablename__ = "election_votes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nation_id: Mapped[int] = mapped_column(Integer, index=True)
    voter_vk_id: Mapped[int] = mapped_column(BigInteger)
    candidate_vk_id: Mapped[int] = mapped_column(BigInteger)
    election_key: Mapped[str] = mapped_column(String(32), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class ChatWar(Base):
    __tablename__ = "chat_wars"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nation_a_id: Mapped[int] = mapped_column(Integer)
    nation_b_id: Mapped[int] = mapped_column(Integer)
    score_a: Mapped[int] = mapped_column(Integer, default=0)
    score_b: Mapped[int] = mapped_column(Integer, default=0)
    stake: Mapped[int] = mapped_column(Integer, default=100)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class InventoryItem(Base):
    __tablename__ = "inventory_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    player_vk_id: Mapped[int] = mapped_column(BigInteger, index=True)
    item_id: Mapped[str] = mapped_column(String(64), index=True)
    qty: Mapped[int] = mapped_column(Integer, default=1)
    # трофеи колеса: продаются дешевле, нельзя выставить на рынок
    bound_qty: Mapped[int] = mapped_column(Integer, default=0)


class EquippedItem(Base):
    __tablename__ = "equipped_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    player_vk_id: Mapped[int] = mapped_column(BigInteger, index=True)
    slot: Mapped[str] = mapped_column(String(16))
    item_id: Mapped[str] = mapped_column(String(64))
    upgrade: Mapped[int] = mapped_column(Integer, default=0)
    # трофей колеса — при снятии снова bound
    bound: Mapped[bool] = mapped_column(Boolean, default=False)


class ItemCharge(Base):
    __tablename__ = "item_charges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    player_vk_id: Mapped[int] = mapped_column(BigInteger, index=True)
    item_id: Mapped[str] = mapped_column(String(64))
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DiscoveredItem(Base):
    __tablename__ = "discovered_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    player_vk_id: Mapped[int] = mapped_column(BigInteger, index=True)
    item_id: Mapped[str] = mapped_column(String(64))
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class PlayerBuff(Base):
    """Временные заряды легенд (например no_tax_3 оставшиеся работы)."""

    __tablename__ = "player_buffs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    player_vk_id: Mapped[int] = mapped_column(BigInteger, index=True)
    buff_code: Mapped[str] = mapped_column(String(32))
    stacks: Mapped[int] = mapped_column(Integer, default=0)
    meta: Mapped[str] = mapped_column(String(128), default="")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MarketListing(Base):
    """P2P-лоты торговой площадки."""

    __tablename__ = "market_listings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    seller_vk_id: Mapped[int] = mapped_column(BigInteger, index=True)
    item_id: Mapped[str] = mapped_column(String(64), index=True)
    rarity: Mapped[str] = mapped_column(String(16), index=True, default="common")
    price: Mapped[int] = mapped_column(Integer)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class NationWeekly(Base):
    __tablename__ = "nation_weeklies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nation_id: Mapped[int] = mapped_column(Integer, index=True)
    week_key: Mapped[str] = mapped_column(String(16), index=True)
    goal_type: Mapped[str] = mapped_column(String(32))
    progress: Mapped[int] = mapped_column(Integer, default=0)
    target: Mapped[int] = mapped_column(Integer, default=40)
    claimed: Mapped[bool] = mapped_column(Boolean, default=False)


class NationRole(Base):
    __tablename__ = "nation_roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nation_id: Mapped[int] = mapped_column(Integer, index=True)
    vk_id: Mapped[int] = mapped_column(BigInteger, index=True)
    role: Mapped[str] = mapped_column(String(16))  # warlord | treasurer | herald


class SeasonScore(Base):
    __tablename__ = "season_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    season_id: Mapped[str] = mapped_column(String(16), index=True)  # YYYY-MM
    nation_id: Mapped[int] = mapped_column(Integer, index=True)
    points: Mapped[int] = mapped_column(Integer, default=0)


class Suggestion(Base):
    """Предложения игроков по обновлениям."""

    __tablename__ = "suggestions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    author_vk_id: Mapped[int] = mapped_column(BigInteger, index=True)
    author_name: Mapped[str] = mapped_column(String(128), default="")
    text: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    # pending | accepted | rejected
    admin_note: Mapped[str] = mapped_column(String(256), default="")
    reward: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class BugReport(Base):
    """Сообщения игроков о багах."""

    __tablename__ = "bug_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    author_vk_id: Mapped[int] = mapped_column(BigInteger, index=True)
    author_name: Mapped[str] = mapped_column(String(128), default="")
    text: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    # pending | accepted | rejected
    admin_note: Mapped[str] = mapped_column(String(256), default="")
    reward: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class NationAlliance(Base):
    """Союз двух стран: вместе сильнее в рейде."""

    __tablename__ = "nation_alliances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # всегда nation_low_id < nation_high_id
    nation_low_id: Mapped[int] = mapped_column(Integer, index=True)
    nation_high_id: Mapped[int] = mapped_column(Integer, index=True)
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    # pending | active
    proposed_by_id: Mapped[int] = mapped_column(Integer, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RaidMusterJoin(Base):
    """Граждане, вступившие в сбор перед рейдом."""

    __tablename__ = "raid_muster_joins"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nation_id: Mapped[int] = mapped_column(Integer, index=True)
    vk_id: Mapped[int] = mapped_column(BigInteger, index=True)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class NationTrophy(Base):
    """Трофейный зал страны."""

    __tablename__ = "nation_trophies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nation_id: Mapped[int] = mapped_column(Integer, index=True)
    item_id: Mapped[str] = mapped_column(String(64), default="")
    item_name: Mapped[str] = mapped_column(String(128), default="")
    from_nation_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class NationContract(Base):
    """Биржа контрактов страны."""

    __tablename__ = "nation_contracts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nation_id: Mapped[int] = mapped_column(Integer, index=True)
    job: Mapped[str] = mapped_column(String(32), default="mine")
    need: Mapped[int] = mapped_column(Integer, default=5)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    reward: Mapped[int] = mapped_column(Integer, default=50)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_by: Mapped[int] = mapped_column(BigInteger, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
