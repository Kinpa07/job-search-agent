from asyncio import sleep
from datetime import UTC, datetime, timedelta

import httpx
import structlog

from app.adapters.base import JobFilters, RawJob

COMPANY_SLUGS = {
    "trading212": "Trading212",
    "elevenlabs": "ElevenLabs",
    "searchapi": "SearchApi",
    "n8n": "n8n",
    "Redis": "Redis",
    "lucidlink": "LucidLink",
    "p2p.org": "P2P.org",
    "duvo": "Duvo",
}


logger = structlog.get_logger()


class AshbyAdapter:
    async def fetch_jobs(self, filters: JobFilters) -> list[RawJob]:
        result = []
        async with httpx.AsyncClient(timeout=60.0) as client:
            for slug, company_name in COMPANY_SLUGS.items():
                try:
                    response = await client.get(
                        f"https://api.ashbyhq.com/posting-api/job-board/{slug}"
                    )
                    response.raise_for_status()
                    jobs = response.json()["jobs"]

                    filtered = jobs

                    if filters.keywords:
                        keywords = [keyword.lower() for keyword in filters.keywords]
                        filtered = [
                            job
                            for job in filtered
                            if any(keyword in job["title"].lower() for keyword in keywords)
                        ]

                    if filters.location:
                        filtered = [
                            job
                            for job in filtered
                            if filters.location.lower() in job["location"].lower()
                        ]

                    if filters.posted_within_days > 0:
                        cutoff = datetime.now(UTC) - timedelta(days=filters.posted_within_days)
                        filtered = [
                            job
                            for job in filtered
                            if datetime.fromisoformat(job["publishedAt"]).astimezone(UTC) > cutoff
                        ]

                    for job in filtered:
                        result.append(
                            RawJob(
                                title=job["title"],
                                company=company_name,
                                location=job.get("location") or None,
                                url=job["jobUrl"],
                                source="ashby",
                                description=job.get("descriptionPlain") or None,
                                raw_html=None,
                            )
                        )

                    logger.info("ashby slug fetched", slug=slug, job_count=len(filtered))

                except httpx.HTTPStatusError as e:
                    if e.response.status_code in {403, 404}:
                        logger.warning(
                            "ashby slug unavailable",
                            slug=slug,
                            status=e.response.status_code,
                        )
                    else:
                        logger.exception("ashby slug fetch failed", slug=slug)
                except Exception:
                    logger.exception("ashby slug fetch failed", slug=slug)

                await sleep(1)

        logger.info("ashby fetch completed", job_count=len(result))
        return result

    def source_name(self) -> str:
        return "ashby"
