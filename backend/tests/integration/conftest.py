import asyncio
import os
from collections.abc import AsyncGenerator
from urllib.parse import urlparse

import asyncpg  # type: ignore[import-untyped]
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.database import Base, get_session
from app.main import app
from app.models.job import Job  # noqa: F401  registers the table on Base.metadata

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5433/jobsearch_test",
)

_parsed = urlparse(TEST_DATABASE_URL)
_TEST_DB_NAME = _parsed.path.lstrip("/")
_ADMIN_DSN = (
    f"postgresql://{_parsed.username}:{_parsed.password}"
    f"@{_parsed.hostname}:{_parsed.port}/postgres"
)


async def _ensure_test_database() -> None:
    """Create the isolated test database if it doesn't exist; skip the test
    if Postgres is unreachable so the suite stays green without a DB."""
    try:
        conn = await asyncio.wait_for(asyncpg.connect(_ADMIN_DSN), timeout=5)
    except (OSError, asyncpg.PostgresError, TimeoutError):
        pytest.skip("Postgres not reachable — skipping integration test")
    try:
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", _TEST_DB_NAME
        )
        if not exists:
            await conn.execute(f'CREATE DATABASE "{_TEST_DB_NAME}"')
    finally:
        await conn.close()


@pytest.fixture
async def engine() -> AsyncGenerator[AsyncEngine, None]:
    await _ensure_test_database()
    eng = create_async_engine(TEST_DATABASE_URL)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield eng
    finally:
        async with eng.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await eng.dispose()


@pytest.fixture
async def db_session(engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest.fixture
async def api_client(engine: AsyncEngine) -> AsyncGenerator[AsyncClient, None]:
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_session() -> AsyncGenerator[AsyncSession, None]:
        async with factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_session, None)
