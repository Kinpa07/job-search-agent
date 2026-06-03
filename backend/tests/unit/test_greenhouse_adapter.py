from collections.abc import Callable
from datetime import datetime
from typing import Any

import httpx
import pytest

from app.adapters.base import JobFilters
from app.adapters.greenhouse import GreenhouseAdapter

PatchHttpx = Callable[[str, Callable[[httpx.Request], httpx.Response]], None]


def _job(
    title: str,
    *,
    location: str = "Sofia",
    content: str = "<p>Build things</p>",
    updated_at: str | None = None,
) -> dict[str, Any]:
    return {
        "title": title,
        "location": {"name": location},
        "content": content,
        "absolute_url": "https://boards.greenhouse.io/testco/jobs/1",
        "updated_at": updated_at or datetime.now().isoformat(),
    }


@pytest.fixture(autouse=True)
def single_slug(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.config.settings.greenhouse_slugs", {"testco": "Test Co"})


async def test_maps_fields_and_strips_html_description(patch_httpx: PatchHttpx) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"jobs": [_job("Junior Developer")]})

    patch_httpx("app.adapters.greenhouse", handler)
    job = (await GreenhouseAdapter().fetch_jobs(JobFilters()))[0]
    assert job.source == "greenhouse"
    assert job.company == "Test Co"
    assert job.location == "Sofia"
    assert job.description == "Build things"


async def test_drops_senior_titles(patch_httpx: PatchHttpx) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"jobs": [_job("Junior Developer"), _job("Staff Engineer")]}
        )

    patch_httpx("app.adapters.greenhouse", handler)
    jobs = await GreenhouseAdapter().fetch_jobs(JobFilters())
    assert [j.title for j in jobs] == ["Junior Developer"]


async def test_unavailable_slug_does_not_abort_other_slugs(
    patch_httpx: PatchHttpx, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "app.config.settings.greenhouse_slugs",
        {"dead": "Dead Co", "live": "Live Co"},
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if "/boards/dead/" in request.url.path:
            return httpx.Response(404)
        return httpx.Response(200, json={"jobs": [_job("Junior Developer")]})

    patch_httpx("app.adapters.greenhouse", handler)
    jobs = await GreenhouseAdapter().fetch_jobs(JobFilters())
    assert [j.company for j in jobs] == ["Live Co"]
