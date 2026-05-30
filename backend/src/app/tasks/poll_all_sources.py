import asyncio
import time

import httpx
import structlog

from app.adapters.arbeitnow import ArbeitNowAdapter
from app.adapters.ashby import AshbyAdapter
from app.adapters.base import JobFilters, JobSource
from app.adapters.devbg import DevBgAdapter
from app.adapters.greenhouse import GreenhouseAdapter
from app.adapters.lever import LeverAdapter
from app.adapters.remotive import RemotiveAdapter
from app.celery_app import celery_app
from app.database import async_session_factory
from app.repositories.job import JobRepository

logger = structlog.get_logger()


@celery_app.task(
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
            source = adapter.source_name()
            try:
                start = time.perf_counter()
                raw_jobs = await adapter.fetch_jobs(JobFilters())
                count = await repo.add_jobs(raw_jobs)
                elapsed = time.perf_counter() - start
                logger.info(
                    "adapter polled",
                    source=source,
                    job_count=len(raw_jobs),
                    new_count=count,
                    elapsed_seconds=round(elapsed, 2),
                )
                result[source] = count
            except httpx.HTTPError as e:
                logger.warning("adapter poll failed", source=source, error=str(e))
                raise

        logger.info("poll_all_sources completed", result=result)
        return result
