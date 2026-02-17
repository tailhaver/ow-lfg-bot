from sqlalchemy import TIMESTAMP, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncEngine, AsyncSession

from os import environ

from datetime import datetime

engine = create_async_engine(environ.get("DATABASE_PATH", "sqlite+aiosqlite:///"))

class Base(DeclarativeBase):
    type_annotation_map = {
        datetime: TIMESTAMP(timezone=True)
    }

class Server(Base):
    __tablename__ = "server"

    id: Mapped[int] = mapped_column(primary_key=True)
    log_channel: Mapped[int] = mapped_column(nullable=True)
    logging_enabled: Mapped[bool] = mapped_column(default=False)
    voice_channel_category: Mapped[int] = mapped_column(nullable=True)

class VoiceChannel(Base):
    __tablename__ = "voicechannel"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner: Mapped[int] = mapped_column(nullable=False)
    has_user: Mapped[bool] = mapped_column(default=False)
    last_leave: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())    

async def init_models():
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: Base.metadata.create_all(
            bind=sync_conn, checkfirst=True))

Session = async_sessionmaker(engine, expire_on_commit=False)
