import asyncio

import httpx
import redis.asyncio as aioredis

from app.adapters.base import JobFilters
from app.celery_app import celery_app
from app.config import settings
from app.database import async_session_factory
from app.repositories.job import JobRepository
from app.services.polling import record_poll_status, run_poll


@celery_app.task(  # type: ignore[untyped-decorator]
    name="app.tasks.poll_all_sources",
    max_retries=3,
    retry_backoff=True,
    autoretry_for=(httpx.HTTPError,),
)
def poll_jobs() -> dict[str, int]:
    return asyncio.run(_poll_jobs())


async def _poll_jobs() -> dict[str, int]:
    async with async_session_factory() as session:
        repo = JobRepository(session)
        result = await run_poll(repo, JobFilters())

    async with aioredis.Redis.from_url(settings.redis_url, decode_responses=True) as redis:
        await record_poll_status(redis, result)

    # Network errors were isolated per-source so every source got a turn and the
    # status was recorded; now re-raise one to let autoretry_for retry the poll.
    if result.exceptions:
        raise result.exceptions[0]

    new_counts: dict[str, int] = {}
    for source, counts in result.counts.items():
        new_counts[source] = counts.new_count
    return new_counts
