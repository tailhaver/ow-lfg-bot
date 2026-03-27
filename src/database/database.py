from datetime import datetime
from os import environ

from sqlalchemy import JSON, TIMESTAMP, DateTime, func, text
from sqlalchemy.ext.asyncio import (
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

engine = create_async_engine(environ.get("DATABASE_PATH", "sqlite+aiosqlite:///"))


class Base(DeclarativeBase):
    type_annotation_map = {datetime: TIMESTAMP(timezone=True)}


class Server(Base):
    __tablename__ = "server"

    id: Mapped[int] = mapped_column(primary_key=True)
    log_channel: Mapped[int] = mapped_column(nullable=True)
    logging_enabled: Mapped[bool] = mapped_column(default=False)
    voice_channel_category: Mapped[int] = mapped_column(nullable=True)
    mythic_prism_roles: Mapped[JSON] = mapped_column(
        JSON, default={}, server_default=text("'{}'"), nullable=True
    )


class VoiceChannel(Base):
    __tablename__ = "voicechannel"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner: Mapped[int] = mapped_column(nullable=False)
    has_user: Mapped[bool] = mapped_column(default=False)
    last_leave: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now()
    )


class Member(Base):
    __tablename__ = "Member"

    guild_id: Mapped[int] = mapped_column(primary_key=True)
    id: Mapped[int] = mapped_column(primary_key=True)
    xp: Mapped[int]
    vc_time: Mapped[float]
    in_vc: Mapped[bool] = mapped_column(default=False)
    last_vc_join: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now()
    )
    next_message_xp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now()
    )
    next_vc_xp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now()
    )
    spent_prisms: Mapped[int] = mapped_column(default=0, nullable=True)
    mythic_inventory: Mapped[JSON] = mapped_column(
        JSON, default=[], server_default=text("'[]'"), nullable=True
    )


async def init_models():
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: Base.metadata.create_all(bind=sync_conn, checkfirst=True)
        )


Session = async_sessionmaker(engine, expire_on_commit=False)
