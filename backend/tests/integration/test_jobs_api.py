import json
from typing import Any

import pytest
import redis.asyncio as aioredis
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters import arbeitnow, ashby, devbg, greenhouse, lever, remotive
from app.adapters.base import JobFilters, RawJob
from app.repositories.job import JobRepository

pytestmark = pytest.mark.integration


def _raw(title: str, source: str = "greenhouse", location: str | None = "Sofia") -> RawJob:
    return RawJob(
        title=title,
        company="Acme",
        location=location,
        url=f"https://jobs.example.com/{title}",
        source=source,
        description="desc",
        raw_html=None,
    )


async def test_list_jobs_empty(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/v1/jobs/")
    assert response.status_code == 200
    assert response.json() == []


async def test_list_jobs_returns_stored(
    api_client: AsyncClient, db_session: AsyncSession
) -> None:
    await JobRepository(db_session).add_jobs([_raw("Backend Engineer")])
    body = (await api_client.get("/api/v1/jobs/")).json()
    assert len(body) == 1
    assert body[0]["title"] == "Backend Engineer"
    assert body[0]["source"] == "greenhouse"


async def test_list_jobs_filters_by_source(
    api_client: AsyncClient, db_session: AsyncSession
) -> None:
    await JobRepository(db_session).add_jobs(
        [_raw("GH Role", source="greenhouse"), _raw("Lever Role", source="lever")]
    )
    body = (await api_client.get("/api/v1/jobs/", params={"source": "lever"})).json()
    assert [j["source"] for j in body] == ["lever"]


async def test_list_jobs_pagination(
    api_client: AsyncClient, db_session: AsyncSession
) -> None:
    await JobRepository(db_session).add_jobs(
        [_raw(f"Role {i}", location=f"City {i}") for i in range(5)]
    )
    body = (await api_client.get("/api/v1/jobs/", params={"limit": 2})).json()
    assert len(body) == 2


async def test_import_stores_jobs(api_client: AsyncClient) -> None:
    payload = [
        {
            "title": "Imported Role",
            "company": "Acme",
            "location": "Sofia",
            "url": "https://linkedin.com/jobs/1",
            "source": "linkedin_extension",
            "description": "desc",
            "raw_html": None,
        }
    ]
    response = await api_client.post("/api/v1/jobs/import", json=payload)
    assert response.status_code == 200
    assert response.json() == 1

    stored = (
        await api_client.get("/api/v1/jobs/", params={"source": "linkedin_extension"})
    ).json()
    assert len(stored) == 1




_SAMPLE_LAST_RUN = {
    "completed_at": "2026-05-30T22:00:00+00:00",
    "counts": {
        "arbeitnow": {"job_count": 10, "new_count": 5},
        "remotive": {"job_count": 3, "new_count": 0},
    },
}


async def test_poll_status_returns_last_run(
    api_client: AsyncClient,
    redis_client: aioredis.Redis,
) -> None:
    await redis_client.set("poll:last_run", json.dumps(_SAMPLE_LAST_RUN))

    response = await api_client.get("/api/v1/jobs/poll/status")
    assert response.status_code == 200
    body = response.json()
    assert body["completed_at"] is not None
    assert body["counts"]["arbeitnow"]["job_count"] == 10
    assert body["counts"]["arbeitnow"]["new_count"] == 5
    assert body["counts"]["remotive"]["new_count"] == 0


async def test_poll_status_never_run(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/v1/jobs/poll/status")
    assert response.status_code == 200
    body = response.json()
    assert body["completed_at"] is None
    assert body["counts"] == {}


async def test_poll_runs_synchronously_and_records_status(
    api_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def empty(self: Any, filters: JobFilters) -> list[RawJob]:
        return []

    async def one(self: Any, filters: JobFilters) -> list[RawJob]:
        return [_raw("Junior Developer", source="arbeitnow")]

    monkeypatch.setattr(arbeitnow.ArbeitNowAdapter, "fetch_jobs", one)
    monkeypatch.setattr(remotive.RemotiveAdapter, "fetch_jobs", empty)
    monkeypatch.setattr(devbg.DevBgAdapter, "fetch_jobs", empty)
    monkeypatch.setattr(greenhouse.GreenhouseAdapter, "fetch_jobs", empty)
    monkeypatch.setattr(lever.LeverAdapter, "fetch_jobs", empty)
    monkeypatch.setattr(ashby.AshbyAdapter, "fetch_jobs", empty)

    response = await api_client.post("/api/v1/jobs/poll")
    assert response.status_code == 200
    body = response.json()
    assert body["completed_at"] is not None
    assert body["counts"]["arbeitnow"]["new_count"] == 1
    assert body["errors"] == {}

    # Ran in-request: the job is stored, not just enqueued for a worker.
    stored = (await api_client.get("/api/v1/jobs/")).json()
    assert [j["title"] for j in stored] == ["Junior Developer"]

    # And the run was recorded so /poll/status reflects it.
    status = (await api_client.get("/api/v1/jobs/poll/status")).json()
    assert status["counts"]["arbeitnow"]["new_count"] == 1
