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


class EquippedItem(Base):
    __tablename__ = "equipped_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    player_vk_id: Mapped[int] = mapped_column(BigInteger, index=True)
    slot: Mapped[str] = mapped_column(String(16))
    item_id: Mapped[str] = mapped_column(String(64))


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
