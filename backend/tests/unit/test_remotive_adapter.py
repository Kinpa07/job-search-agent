from collections.abc import Callable
from datetime import datetime
from typing import Any

import httpx
import pytest

from app.adapters.base import JobFilters
from app.adapters.remotive import RemotiveAdapter

PatchHttpx = Callable[[str, Callable[[httpx.Request], httpx.Response]], None]


def _job(
    title: str,
    *,
    tags: list[str] | None = None,
    location: str = "Worldwide",
    publication_date: str | None = None,
) -> dict[str, Any]:
    return {
        "title": title,
        "company_name": "Acme",
        "candidate_required_location": location,
        "url": "https://remotive.com/jobs/1",
        "description": "desc",
        "tags": tags or [],
        "publication_date": publication_date or datetime.now().isoformat(),
    }


@pytest.fixture
def mock_remotive(patch_httpx: PatchHttpx) -> Callable[[list[dict[str, Any]]], None]:
    def install(jobs: list[dict[str, Any]]) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"jobs": jobs})

        patch_httpx("app.adapters.remotive", handler)

    return install


async def test_drops_senior_titles(
    mock_remotive: Callable[[list[dict[str, Any]]], None],
) -> None:
    mock_remotive([_job("Junior Developer"), _job("Senior Developer")])
    jobs = await RemotiveAdapter().fetch_jobs(JobFilters())
    assert [j.title for j in jobs] == ["Junior Developer"]


async def test_maps_rawjob_fields(
    mock_remotive: Callable[[list[dict[str, Any]]], None],
) -> None:
    mock_remotive([_job("Junior Developer", location="Europe")])
    job = (await RemotiveAdapter().fetch_jobs(JobFilters()))[0]
    assert job.source == "remotive"
    assert job.company == "Acme"
    assert job.location == "Europe"


async def test_drops_stale_jobs(
    mock_remotive: Callable[[list[dict[str, Any]]], None],
) -> None:
    old = (datetime.now().replace(year=datetime.now().year - 1)).isoformat()
    mock_remotive([_job("Junior Developer", publication_date=old)])
    jobs = await RemotiveAdapter().fetch_jobs(JobFilters(posted_within_days=7))
    assert jobs == []


async def test_http_error_propagates(patch_httpx: PatchHttpx) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    patch_httpx("app.adapters.remotive", handler)
    with pytest.raises(httpx.HTTPError):
        await RemotiveAdapter().fetch_jobs(JobFilters())
