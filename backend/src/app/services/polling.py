import json
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime

import httpx
import redis.asyncio as aioredis
import structlog

from app.adapters.arbeitnow import ArbeitNowAdapter
from app.adapters.ashby import AshbyAdapter
from app.adapters.base import JobFilters, JobSource
from app.adapters.devbg import DevBgAdapter
from app.adapters.greenhouse import GreenhouseAdapter
from app.adapters.lever import LeverAdapter
from app.adapters.remotive import RemotiveAdapter
from app.repositories.job import JobRepository
from app.schemas.poll_status import SourceCount

logger = structlog.get_logger()

POLL_STATUS_KEY = "poll:last_run"


@dataclass
class PollResult:
    counts: dict[str, SourceCount] = field(default_factory=dict)
    errors: dict[str, str] = field(default_factory=dict)
    # Network exceptions retained so a caller with retry semantics (the Celery
    # task) can re-raise one to trigger autoretry_for.
    exceptions: list[httpx.HTTPError] = field(default_factory=list)


def build_adapters() -> list[JobSource]:
    return [
        ArbeitNowAdapter(),
        RemotiveAdapter(),
        DevBgAdapter(),
        GreenhouseAdapter(),
        LeverAdapter(),
        AshbyAdapter(),
    ]


async def run_poll(repo: JobRepository, filters: JobFilters) -> PollResult:
    """Poll every source once, isolating failures per source.

    A network error (``httpx.HTTPError``) from one adapter is recorded and the
    loop continues, so a single down source can't starve the healthy ones. The
    exception is retained on the result; the Celery task re-raises it to drive
    ``autoretry_for``. Parsing errors are swallowed inside each adapter and never
    reach here.
    """
    result = PollResult()
    for adapter in build_adapters():
        source = adapter.source_name()
        try:
            start = time.perf_counter()
            raw_jobs = await adapter.fetch_jobs(filters)
            new_count = await repo.add_jobs(raw_jobs)
            elapsed = time.perf_counter() - start
            logger.info(
                "adapter polled",
                source=source,
                job_count=len(raw_jobs),
                new_count=new_count,
                elapsed_seconds=round(elapsed, 2),
            )
            result.counts[source] = SourceCount(job_count=len(raw_jobs), new_count=new_count)
        except httpx.HTTPError as e:
            logger.warning("adapter poll failed", source=source, error=str(e))
            result.errors[source] = str(e)
            result.exceptions.append(e)

    logger.info("poll completed", polled=len(result.counts), failed=len(result.errors))
    return result


async def record_poll_status(redis: aioredis.Redis, result: PollResult) -> None:
    """Persist the latest poll outcome so ``GET /poll/status`` can report it."""
    await redis.set(
        POLL_STATUS_KEY,
        json.dumps(
            {
                "completed_at": datetime.now(UTC).isoformat(),
                "counts": {
                    source: c.model_dump()
                    for source, c in result.counts.items()
                },
                "errors": result.errors,
            }
        ),
    )
