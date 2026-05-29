import time

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.arbeitnow import ArbeitNowAdapter
from app.adapters.ashby import AshbyAdapter
from app.adapters.base import JobFilters, JobSource, RawJob
from app.adapters.devbg import DevBgAdapter
from app.adapters.greenhouse import GreenhouseAdapter
from app.adapters.lever import LeverAdapter
from app.adapters.remotive import RemotiveAdapter
from app.database import get_session
from app.repositories.job import JobRepository
from app.schemas.job import JobResponse

router = APIRouter(prefix="/jobs", tags=["jobs"])
logger = structlog.get_logger()


@router.get("/")
async def get_jobs(
    source: str | None = None,
    offset: int = 0,
    limit: int = 100,
    session: AsyncSession = Depends(get_session),
) -> list[JobResponse]:
    repo = JobRepository(session)
    jobs = await repo.get_jobs(source=source, offset=offset, limit=limit)
    return [JobResponse.model_validate(job) for job in jobs]


@router.post("/poll")
async def poll_jobs(
    keywords: list[str] | None = None,
    session: AsyncSession = Depends(get_session),
) -> dict[str, int]:
    filters = JobFilters(keywords=keywords or [])
    repo = JobRepository(session)

    adapters: list[JobSource] = [
        ArbeitNowAdapter(),
        RemotiveAdapter(),
        DevBgAdapter(),
        GreenhouseAdapter(),
        LeverAdapter(),
        AshbyAdapter(),
    ]

    result: dict[str, int] = {}
    for adapter in adapters:
        start = time.perf_counter()
        raw_jobs = await adapter.fetch_jobs(filters)
        count = await repo.add_jobs(raw_jobs)
        elapsed = time.perf_counter() - start
        logger.info(
            "adapter polled",
            source=adapter.source_name(),
            job_count=len(raw_jobs),
            new_count=count,
            elapsed_seconds=round(elapsed, 2),
        )
        result[adapter.source_name()] = count

    return result


@router.post("/import")
async def import_jobs(
    jobs: list[RawJob],
    session: AsyncSession = Depends(get_session),
) -> int:
    repo = JobRepository(session)
    return await repo.add_jobs(jobs)
