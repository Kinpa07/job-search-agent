from collections.abc import Callable
from datetime import datetime
from typing import Any

import httpx
import pytest

from app.adapters.ashby import AshbyAdapter
from app.adapters.base import JobFilters

PatchHttpx = Callable[[str, Callable[[httpx.Request], httpx.Response]], None]


def _job(
    title: str,
    *,
    location: str = "Remote",
    published_at: str | None = None,
) -> dict[str, Any]:
    return {
        "title": title,
        "location": location,
        "jobUrl": "https://jobs.ashbyhq.com/testco/1",
        "descriptionPlain": "desc",
        "publishedAt": published_at or datetime.now().isoformat(),
    }


@pytest.fixture(autouse=True)
def single_slug(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.adapters.ashby.COMPANY_SLUGS", {"testco": "Test Co"})


@pytest.fixture(autouse=True)
def fast_sleep(no_sleep: Callable[[str], None]) -> None:
    no_sleep("app.adapters.ashby")


async def test_maps_rawjob_fields(patch_httpx: PatchHttpx) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"jobs": [_job("Junior Developer")]})

    patch_httpx("app.adapters.ashby", handler)
    job = (await AshbyAdapter().fetch_jobs(JobFilters()))[0]
    assert job.source == "ashby"
    assert job.company == "Test Co"
    assert job.url == "https://jobs.ashbyhq.com/testco/1"


async def test_drops_senior_titles(patch_httpx: PatchHttpx) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"jobs": [_job("Junior Developer"), _job("Principal Engineer")]}
        )

    patch_httpx("app.adapters.ashby", handler)
    jobs = await AshbyAdapter().fetch_jobs(JobFilters())
    assert [j.title for j in jobs] == ["Junior Developer"]


async def test_drops_stale_jobs(patch_httpx: PatchHttpx) -> None:
    old = datetime.now().replace(year=datetime.now().year - 1).isoformat()
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"jobs": [_job("Junior Developer", published_at=old)]})

    patch_httpx("app.adapters.ashby", handler)
    jobs = await AshbyAdapter().fetch_jobs(JobFilters(posted_within_days=7))
    assert jobs == []
