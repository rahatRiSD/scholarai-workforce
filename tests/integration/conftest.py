"""Shared fixtures for integration tests: a fully wired, offline-mode container.

Uses an in-memory SQLite database and an in-memory Qdrant instance so these
tests need no external services, but they do exercise the real
composition root, the real SQLAlchemy models, and the real Qdrant client —
unlike the unit tests, which fake those out. Every test in this package
skips cleanly if its required package (sqlalchemy/aiosqlite/qdrant-client/
fastapi) isn't installed.
"""

from __future__ import annotations

import pytest
import pytest_asyncio

pytest.importorskip("sqlalchemy")
pytest.importorskip("aiosqlite")
pytest.importorskip("qdrant_client")

from scholarai.composition import Container, bootstrap, build_container  # noqa: E402
from scholarai.infrastructure.config.settings import (  # noqa: E402
    DatabaseSettings,
    Environment,
    Settings,
    VectorStoreSettings,
    WebSearchSettings,
)


@pytest_asyncio.fixture
async def container(tmp_path) -> Container:
    # A temp *file* database, not ``:memory:`` - SQLite's in-memory mode gives
    # each new pooled connection its own separate database, which silently
    # breaks "write in one request, read in the next" tests.
    db_path = tmp_path / "test.db"
    settings = Settings(
        environment=Environment.DEVELOPMENT,
        database=DatabaseSettings(url=f"sqlite+aiosqlite:///{db_path}"),
        vectorstore=VectorStoreSettings(url=None),
        websearch=WebSearchSettings(enabled=False),
        knowledge_base_dir=tmp_path / "empty_kb",
        uploads_dir=tmp_path / "uploads",
    )
    built = build_container(settings)
    await bootstrap(built)
    return built
