import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.base import RawJob
from app.repositories.job import JobRepository

pytestmark = pytest.mark.integration


def _raw(
    title: str = "Backend Engineer",
    company: str = "Acme",
    location: str | None = "Sofia",
    url: str = "https://jobs.example.com/role",
    source: str = "greenhouse",
    description: str | None = "desc",
) -> RawJob:
    return RawJob(
        title=title,
        company=company,
        location=location,
        url=url,
        source=source,
        description=description,
        raw_html=None,
    )


async def test_inserts_distinct_jobs(db_session: AsyncSession) -> None:
    repo = JobRepository(db_session)
    added = await repo.add_jobs(
        [_raw(title="Backend Engineer"), _raw(title="Frontend Engineer")]
    )
    assert added == 2
    assert len(await repo.get_jobs()) == 2


async def test_dedups_identical_content_across_calls(db_session: AsyncSession) -> None:
    repo = JobRepository(db_session)
    assert await repo.add_jobs([_raw()]) == 1
    assert await repo.add_jobs([_raw()]) == 0
    assert len(await repo.get_jobs()) == 1


async def test_dedup_key_is_title_company_location_only(db_session: AsyncSession) -> None:
    repo = JobRepository(db_session)
    await repo.add_jobs([_raw(url="https://a.com/1", description="first")])
    # Same title+company+location but different url/description still dedups,
    # because content_hash is built only from title+company+location.
    added = await repo.add_jobs([_raw(url="https://b.com/2", description="second")])
    assert added == 0
    assert len(await repo.get_jobs()) == 1


async def test_dedups_within_a_single_batch(db_session: AsyncSession) -> None:
    repo = JobRepository(db_session)
    added = await repo.add_jobs([_raw(), _raw()])  # identical content twice
    assert added == 1
    assert len(await repo.get_jobs()) == 1


async def test_different_location_is_distinct(db_session: AsyncSession) -> None:
    repo = JobRepository(db_session)
    added = await repo.add_jobs(
        [_raw(location="Sofia"), _raw(location="Plovdiv")]
    )
    assert added == 2


async def test_empty_batch_returns_zero(db_session: AsyncSession) -> None:
    repo = JobRepository(db_session)
    assert await repo.add_jobs([]) == 0


async def test_get_jobs_filters_by_source(db_session: AsyncSession) -> None:
    repo = JobRepository(db_session)
    await repo.add_jobs(
        [
            _raw(title="GH Role", source="greenhouse"),
            _raw(title="Lever Role", source="lever"),
        ]
    )
    lever_jobs = await repo.get_jobs(source="lever")
    assert [j.source for j in lever_jobs] == ["lever"]
