from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Nation(Base):
    __tablename__ = "nations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_peer_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(64))
    flag_emoji: Mapped[str] = mapped_column(String(16), default="🏛")
    leader_id: Mapped[int] = mapped_column(BigInteger, index=True)
    treasury: Mapped[int] = mapped_column(Integer, default=0)
    last_raid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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
