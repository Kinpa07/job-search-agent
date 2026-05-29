from collections.abc import Callable
from datetime import datetime
from typing import Any

import httpx
import pytest

from app.adapters.arbeitnow import ArbeitNowAdapter
from app.adapters.base import JobFilters

PatchHttpx = Callable[[str, Callable[[httpx.Request], httpx.Response]], None]

RECENT = datetime.now().timestamp()


def _job(
    title: str,
    *,
    job_types: list[str] | None = None,
    tags: list[str] | None = None,
    created_at: float = RECENT,
) -> dict[str, Any]:
    return {
        "title": title,
        "company_name": "Acme",
        "location": "Remote",
        "url": f"https://arbeitnow.com/jobs/{title}",
        "description": "desc",
        "tags": tags or [],
        "job_types": job_types or ["entry"],
        "remote": True,
        "created_at": created_at,
    }


@pytest.fixture
def mock_arbeitnow(patch_httpx: PatchHttpx) -> Callable[[list[dict[str, Any]]], None]:
    def install(jobs: list[dict[str, Any]]) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"data": jobs})

        patch_httpx("app.adapters.arbeitnow", handler)

    return install


async def test_drops_senior_and_non_technical_titles(
    mock_arbeitnow: Callable[[list[dict[str, Any]]], None],
) -> None:
    mock_arbeitnow(
        [
            _job("Junior Backend Developer"),
            _job("Senior Backend Developer"),
            _job("Project Manager"),
        ]
    )
    jobs = await ArbeitNowAdapter().fetch_jobs(JobFilters())
    assert [j.title for j in jobs] == ["Junior Backend Developer"]


async def test_maps_rawjob_fields(
    mock_arbeitnow: Callable[[list[dict[str, Any]]], None],
) -> None:
    mock_arbeitnow([_job("Junior Developer")])
    job = (await ArbeitNowAdapter().fetch_jobs(JobFilters()))[0]
    assert job.company == "Acme"
    assert job.source == "arbeitnow"
    assert job.location == "Remote"
    assert job.raw_html is None


async def test_drops_stale_jobs(
    mock_arbeitnow: Callable[[list[dict[str, Any]]], None],
) -> None:
    five_days_ago = datetime.now().timestamp() - 60 * 60 * 24 * 5
    mock_arbeitnow([_job("Junior Developer", created_at=five_days_ago)])
    jobs = await ArbeitNowAdapter().fetch_jobs(JobFilters(posted_within_days=1))
    assert jobs == []


async def test_keyword_filter_matches_title(
    mock_arbeitnow: Callable[[list[dict[str, Any]]], None],
) -> None:
    mock_arbeitnow(
        [
            _job("Junior Python Developer"),
            _job("Junior Java Developer"),
        ]
    )
    jobs = await ArbeitNowAdapter().fetch_jobs(JobFilters(keywords=["python"]))
    assert [j.title for j in jobs] == ["Junior Python Developer"]


async def test_network_error_returns_empty_list(patch_httpx: PatchHttpx) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    patch_httpx("app.adapters.arbeitnow", handler)
    assert await ArbeitNowAdapter().fetch_jobs(JobFilters()) == []
