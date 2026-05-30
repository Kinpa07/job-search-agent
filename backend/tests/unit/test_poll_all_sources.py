import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

import app.tasks.poll_all_sources as task_module
from app.adapters import arbeitnow, ashby, devbg, greenhouse, lever, remotive
from app.adapters.base import JobFilters, RawJob
from app.repositories.job import JobRepository
from app.tasks.poll_all_sources import _poll_jobs


def _raw(title: str, source: str) -> RawJob:
    return RawJob(
        title=title,
        company="Acme",
        location="Sofia",
        url=f"https://example.com/{title}",
        source=source,
        description="desc",
        raw_html=None,
    )


@pytest.fixture
def mock_session_factory(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=MagicMock())
    mock_ctx.__aexit__ = AsyncMock(return_value=False)
    monkeypatch.setattr(task_module, "async_session_factory", MagicMock(return_value=mock_ctx))


@pytest.fixture
def mock_redis(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    redis = AsyncMock()
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=redis)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)
    monkeypatch.setattr(task_module.aioredis, "from_url", MagicMock(return_value=mock_ctx))
    return redis


async def test_poll_all_sources_returns_counts_and_writes_redis(
    monkeypatch: pytest.MonkeyPatch,
    mock_session_factory: None,
    mock_redis: AsyncMock,
) -> None:
    async def one(self: Any, filters: JobFilters) -> list[RawJob]:
        return [_raw("Junior Developer", "arbeitnow")]

    async def empty(self: Any, filters: JobFilters) -> list[RawJob]:
        return []

    monkeypatch.setattr(arbeitnow.ArbeitNowAdapter, "fetch_jobs", one)
    monkeypatch.setattr(remotive.RemotiveAdapter, "fetch_jobs", empty)
    monkeypatch.setattr(devbg.DevBgAdapter, "fetch_jobs", empty)
    monkeypatch.setattr(greenhouse.GreenhouseAdapter, "fetch_jobs", empty)
    monkeypatch.setattr(lever.LeverAdapter, "fetch_jobs", empty)
    monkeypatch.setattr(ashby.AshbyAdapter, "fetch_jobs", empty)

    async def fake_add_jobs(self: Any, jobs: list[RawJob]) -> int:
        return len(jobs)

    monkeypatch.setattr(JobRepository, "add_jobs", fake_add_jobs)

    result = await _poll_jobs()

    assert result["arbeitnow"] == 1
    assert result["remotive"] == 0

    mock_redis.set.assert_called_once()
    key, raw = mock_redis.set.call_args[0]
    payload = json.loads(raw)

    assert key == "poll:last_run"
    assert "completed_at" in payload
    assert payload["counts"]["arbeitnow"]["job_count"] == 1
    assert payload["counts"]["arbeitnow"]["new_count"] == 1
    assert payload["counts"]["remotive"]["job_count"] == 0
    assert payload["counts"]["remotive"]["new_count"] == 0
