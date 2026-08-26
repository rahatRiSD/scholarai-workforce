"""Async SQLAlchemy engine/session setup.

Works unmodified against SQLite (the zero-setup laptop default,
``aiosqlite``) or PostgreSQL (``asyncpg``, via Docker Compose) — the only
difference is ``DATABASE_URL``. Integration tests that need a real Postgres
skip automatically when one isn't reachable; the SQLite path always runs.
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from scholarai.infrastructure.database.models import Base


def build_engine(database_url: str, *, echo: bool = False) -> AsyncEngine:
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if database_url.startswith("sqlite"):
        # e.g. sqlite+aiosqlite:////abs/path/data/scholarai.db - make sure the dir exists.
        path_part = database_url.split("///")[-1]
        if path_part and path_part != ":memory:":
            Path(path_part).parent.mkdir(parents=True, exist_ok=True)
    return create_async_engine(database_url, echo=echo)


def get_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


async def create_all(engine: AsyncEngine) -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
