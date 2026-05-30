from collections.abc import Callable
from datetime import datetime

import httpx
import pytest

from app.adapters.base import JobFilters
from app.adapters.devbg import BG_MONTHS, DevBgAdapter

PatchHttpx = Callable[[str, Callable[[httpx.Request], httpx.Response]], None]

_REV_MONTHS = {month: abbr for abbr, month in BG_MONTHS.items()}
_DETAIL_HTML = '<div class="job_description">Job details here</div>'


def _today_str() -> str:
    now = datetime.now()
    return f"{now.day} {_REV_MONTHS[now.month]}"


def _card(title: str, date_str: str, href: str, company: str = "DevCo") -> str:
    return f"""
    <div class="job-list-item">
      <h6 class="job-title">{title}</h6>
      <span class="company-name">{company}</span>
      <span class="date">{date_str}</span>
      <a class="overlay-link" href="{href}"></a>
      <span class="badge">Sofia</span>
    </div>"""


def _list_page(cards: list[str]) -> str:
    return "<html><body>" + "".join(cards) + "</body></html>"


def _make_handler(pages: dict[str, str]) -> Callable[[httpx.Request], httpx.Response]:
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if "junior-intern" in path:
            return httpx.Response(200, text=pages.get(path, _list_page([])))
        return httpx.Response(200, text=_DETAIL_HTML)

    return handler


@pytest.fixture(autouse=True)
def fast_sleep(no_sleep: Callable[[str], None]) -> None:
    no_sleep("app.adapters.devbg")


async def test_filters_titles_and_maps_fields(patch_httpx: PatchHttpx) -> None:
    pages = {
        "/company/jobs/junior-intern": _list_page(
            [
                _card("Junior Backend Developer", _today_str(), "https://dev.bg/job/1/"),
                _card("Project Manager", _today_str(), "https://dev.bg/job/2/"),
            ]
        ),
    }
    patch_httpx("app.adapters.devbg", _make_handler(pages))
    jobs = await DevBgAdapter().fetch_jobs(JobFilters(posted_within_days=7))
    assert [j.title for j in jobs] == ["Junior Backend Developer"]
    assert jobs[0].source == "dev.bg"
    assert jobs[0].company == "DevCo"
    assert jobs[0].description == "Job details here"


async def test_unparseable_date_does_not_abort_pagination(patch_httpx: PatchHttpx) -> None:
    # A bad date on page 1 must drop only that card; pagination must continue
    # to page 2 (regression test for the per-card date-parse guard).
    pages = {
        "/company/jobs/junior-intern": _list_page(
            [
                _card("Junior QA", "not-a-date", "https://dev.bg/job/1/"),
                _card("Junior Developer", _today_str(), "https://dev.bg/job/2/"),
            ]
        ),
        "/company/jobs/junior-intern/page/2": _list_page(
            [_card("Junior Tester", _today_str(), "https://dev.bg/job/3/")]
        ),
    }
    patch_httpx("app.adapters.devbg", _make_handler(pages))
    jobs = await DevBgAdapter().fetch_jobs(JobFilters(posted_within_days=7))
    assert {j.title for j in jobs} == {"Junior Developer", "Junior Tester"}


async def test_404_last_page_returns_empty_list(patch_httpx: PatchHttpx) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    patch_httpx("app.adapters.devbg", handler)
    assert await DevBgAdapter().fetch_jobs(JobFilters()) == []
