import json
from datetime import UTC, datetime

import redis.asyncio as aioredis
import structlog
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.base import JobFilters, RawJob
from app.database import get_session
from app.dependencies import get_redis
from app.repositories.job import JobRepository
from app.repositories.profile import UserProfileRepository
from app.schemas.job import JobResponse
from app.schemas.poll_status import PollStatusResponse
from app.services.polling import POLL_STATUS_KEY, record_poll_status, run_poll

logger = structlog.get_logger()

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
    redis: aioredis.Redis = Depends(get_redis),
) -> PollStatusResponse:
    """Run a poll synchronously and persist status to Redis.

    Manual trigger / script automation entry point. Celery Beat (Module 2) is
    the normal driver; this endpoint is what you hit when you want to force a
    poll right now without waiting for the next scheduled run.

    ``keywords`` is an explicit override for ad-hoc/test polls. When omitted, the
    poll is profile-driven exactly like the scheduled task: keywords come from the
    confirmed profile, and with no confirmed profile the poll is skipped (rather
    than running unfiltered and flooding the DB).
    """
    if keywords is None:
        profile = await UserProfileRepository(session).get_confirmed()
        if profile is None:
            logger.info("poll.skipped", reason="no confirmed profile")
            return PollStatusResponse(completed_at=None, counts={})
        keywords = profile.search_keywords

    repo = JobRepository(session)
    result = await run_poll(repo, JobFilters(keywords=keywords))
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
