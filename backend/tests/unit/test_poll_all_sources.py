import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

import app.tasks.poll_all_sources as task_module
from app.adapters import arbeitnow, ashby, devbg, greenhouse, lever, remotive
from app.adapters.base import JobFilters, RawJob
from app.models.profile import UserProfile
from app.repositories.job import JobRepository
from app.repositories.profile import UserProfileRepository
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
def mock_confirmed_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    """The poll loads the confirmed profile's keywords; give it one so it proceeds."""
    profile = UserProfile(status="confirmed", search_keywords=["Backend Engineer"])
    monkeypatch.setattr(UserProfileRepository, "get_confirmed", AsyncMock(return_value=profile))


@pytest.fixture
def mock_redis(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    redis = AsyncMock()
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=redis)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)
    monkeypatch.setattr(
        "app.tasks.poll_all_sources.aioredis.Redis.from_url", MagicMock(return_value=mock_ctx)
    )
    return redis


async def test_poll_all_sources_returns_counts_and_writes_redis(
    monkeypatch: pytest.MonkeyPatch,
    mock_session_factory: None,
    mock_confirmed_profile: None,
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


async def test_poll_reraises_network_error_after_recording_status(
    monkeypatch: pytest.MonkeyPatch,
    mock_session_factory: None,
    mock_confirmed_profile: None,
    mock_redis: AsyncMock,
) -> None:
    async def boom(self: Any, filters: JobFilters) -> list[RawJob]:
        raise httpx.ConnectError("arbeitnow unreachable")

    async def empty(self: Any, filters: JobFilters) -> list[RawJob]:
        return []

    monkeypatch.setattr(arbeitnow.ArbeitNowAdapter, "fetch_jobs", boom)
    monkeypatch.setattr(remotive.RemotiveAdapter, "fetch_jobs", empty)
    monkeypatch.setattr(devbg.DevBgAdapter, "fetch_jobs", empty)
    monkeypatch.setattr(greenhouse.GreenhouseAdapter, "fetch_jobs", empty)
    monkeypatch.setattr(lever.LeverAdapter, "fetch_jobs", empty)
    monkeypatch.setattr(ashby.AshbyAdapter, "fetch_jobs", empty)

    async def fake_add_jobs(self: Any, jobs: list[RawJob]) -> int:
        return len(jobs)

    monkeypatch.setattr(JobRepository, "add_jobs", fake_add_jobs)

    # A network error propagates so Celery's autoretry_for can retry the task.
    with pytest.raises(httpx.HTTPError):
        await _poll_jobs()

    # But the failure was recorded first, and the healthy sources were still
    # polled — one down source doesn't abort the whole run.
    mock_redis.set.assert_called_once()
    payload = json.loads(mock_redis.set.call_args[0][1])
    assert "arbeitnow" in payload["errors"]
    assert payload["counts"]["remotive"]["new_count"] == 0
    assert "arbeitnow" not in payload["counts"]


async def test_poll_skips_when_no_confirmed_profile(
    monkeypatch: pytest.MonkeyPatch,
    mock_session_factory: None,
    mock_redis: AsyncMock,
) -> None:
    monkeypatch.setattr(UserProfileRepository, "get_confirmed", AsyncMock(return_value=None))

    result = await _poll_jobs()

    # No profile → no keywords → the poll is a no-op (no sources hit, no status written).
    assert result == {}
    mock_redis.set.assert_not_called()
