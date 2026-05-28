from asyncio import sleep
from datetime import UTC, datetime, timedelta

import httpx
import structlog

from app.adapters.base import JobFilters, RawJob

COMPANY_SLUGS = {
    "Fliff": "Fliff",
    "capital": "Capital.com",
    "crypto": "Crypto.com",
    "binance": "Binance",
    "OpenPayd": "OpenPayd",
    "doola": "doola",
    "remofirst": "RemoFirst",
    "pipedrive": "Pipedrive",
}


logger = structlog.get_logger()


class LeverAdapter:
    async def fetch_jobs(self, filters: JobFilters) -> list[RawJob]:
        result = []
        async with httpx.AsyncClient() as client:
            for slug, company_name in COMPANY_SLUGS.items():
                try:
                    response = await client.get(
                        f"https://api.lever.co/v0/postings/{slug}?mode=json"
                    )
                    response.raise_for_status()
                    jobs = response.json()

                    filtered = jobs

                    if filters.keywords:
                        keywords = [keyword.lower() for keyword in filters.keywords]
                        filtered = [
                            job
                            for job in filtered
                            if any(keyword in job["text"].lower() for keyword in keywords)
                        ]

                    if filters.location:
                        filtered = [
                            job
                            for job in filtered
                            if filters.location.lower()
                            in job.get("categories", {}).get("location", "").lower()
                        ]

                    if filters.posted_within_days > 0:
                        cutoff = datetime.now(UTC) - timedelta(days=filters.posted_within_days)
                        filtered = [
                            job
                            for job in filtered
                            if datetime.fromtimestamp(job["createdAt"] / 1000, tz=UTC) > cutoff
                        ]

                    for job in filtered:
                        result.append(
                            RawJob(
                                title=job["text"],
                                company=company_name,
                                location=job.get("categories", {}).get("location") or None,
                                url=job["hostedUrl"],
                                source="lever",
                                description=job.get("descriptionPlain") or None,
                                raw_html=None,
                            )
                        )

                    logger.info("lever slug fetched", slug=slug, job_count=len(filtered))

                except httpx.HTTPStatusError as e:
                    if e.response.status_code in {403, 404}:
                        logger.warning(
                            "lever slug unavailable",
                            slug=slug,
                            status=e.response.status_code,
                        )
                    else:
                        logger.exception("lever slug fetch failed", slug=slug)
                except Exception:
                    logger.exception("lever slug fetch failed", slug=slug)

                await sleep(1)

        logger.info("lever fetch completed", job_count=len(result))
        return result

    def source_name(self) -> str:
        return "lever"
