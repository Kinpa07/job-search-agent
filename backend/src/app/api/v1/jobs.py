import json
from datetime import UTC, datetime

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.base import JobFilters, RawJob
from app.database import get_session
from app.dependencies import get_redis
from app.repositories.job import JobRepository
from app.schemas.job import JobResponse
from app.schemas.poll_status import PollStatusResponse
from app.services.polling import POLL_STATUS_KEY, record_poll_status, run_poll

router = APIRouter(prefix="/jobs", tags=["jobs"])


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


@router.get("/poll/status")
async def get_poll_status(redis: aioredis.Redis = Depends(get_redis)) -> PollStatusResponse:
    last_run = await redis.get(POLL_STATUS_KEY)
    if last_run:
        return PollStatusResponse(**json.loads(last_run))
    return PollStatusResponse(completed_at=None, counts={})


@router.post("/poll")
async def poll_jobs(
    keywords: list[str] | None = None,
    session: AsyncSession = Depends(get_session),
) -> dict[str, int]:
    repo = JobRepository(session)
    result = await run_poll(repo, JobFilters(keywords=keywords or []))
    new_counts: dict[str, int] = {}
    for source, counts in result.counts.items():
        new_counts[source] = counts.new_count
    return new_counts


@router.post("/poll/trigger")
async def trigger_polling(
    session: AsyncSession = Depends(get_session),
    redis: aioredis.Redis = Depends(get_redis),
) -> PollStatusResponse:
    """Run a poll synchronously, in-request — the free-tier deployment has no
    always-on worker, so an external cron (cron-job.org) hits this and the work
    must happen here rather than being enqueued for a worker that isn't running."""
    repo = JobRepository(session)
    result = await run_poll(repo, JobFilters())
    await record_poll_status(redis, result)
    return PollStatusResponse(
        completed_at=datetime.now(UTC),
        counts=result.counts,
        errors=result.errors,
    )


@router.post("/import")
async def import_jobs(
    jobs: list[RawJob],
    session: AsyncSession = Depends(get_session),
) -> int:
    repo = JobRepository(session)
    return await repo.add_jobs(jobs)
