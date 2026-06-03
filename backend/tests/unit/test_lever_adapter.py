from collections.abc import Callable
from datetime import datetime
from typing import Any

import httpx
import pytest

from app.adapters.base import JobFilters
from app.adapters.lever import LeverAdapter

PatchHttpx = Callable[[str, Callable[[httpx.Request], httpx.Response]], None]


def _job(
    text: str,
    *,
    location: str = "Remote",
    created_at_ms: int | None = None,
) -> dict[str, Any]:
    return {
        "text": text,
        "categories": {"location": location},
        "createdAt": created_at_ms
        if created_at_ms is not None
        else int(datetime.now().timestamp() * 1000),
        "hostedUrl": "https://jobs.lever.co/testco/1",
        "descriptionPlain": "desc",
    }


@pytest.fixture(autouse=True)
def single_slug(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.config.settings.lever_slugs", {"testco": "Test Co"})


@pytest.fixture(autouse=True)
def fast_sleep(no_sleep: Callable[[str], None]) -> None:
    no_sleep("app.adapters.lever")


async def test_maps_fields_from_text_field(patch_httpx: PatchHttpx) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[_job("Junior Developer")])

    patch_httpx("app.adapters.lever", handler)
    job = (await LeverAdapter().fetch_jobs(JobFilters()))[0]
    assert job.title == "Junior Developer"
    assert job.source == "lever"
    assert job.company == "Test Co"
    assert job.location == "Remote"


async def test_drops_senior_titles(patch_httpx: PatchHttpx) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json=[_job("Junior Developer"), _job("Lead Developer")]
        )

    patch_httpx("app.adapters.lever", handler)
    jobs = await LeverAdapter().fetch_jobs(JobFilters())
    assert [j.title for j in jobs] == ["Junior Developer"]


async def test_drops_stale_jobs(patch_httpx: PatchHttpx) -> None:
    old_ms = int((datetime.now().timestamp() - 60 * 60 * 24 * 5) * 1000)
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[_job("Junior Developer", created_at_ms=old_ms)])

    patch_httpx("app.adapters.lever", handler)
    jobs = await LeverAdapter().fetch_jobs(JobFilters(posted_within_days=1))
    assert jobs == []
