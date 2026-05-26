from datetime import datetime, timedelta

import httpx
import structlog

from app.adapters.base import JobFilters, RawJob

logger = structlog.get_logger()


class ArbeitNowAdapter:
    async def fetch_jobs(self, filters: JobFilters) -> list[RawJob]:
        result = []
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get("https://arbeitnow.com/api/job-board-api")
                response.raise_for_status()
                data = response.json()["data"]

                filtered = data

                if filters.keywords:
                    keywords = [keyword.lower() for keyword in filters.keywords]
                    filtered = [
                        job
                        for job in filtered
                        if any(keyword in job["title"].lower() for keyword in keywords)
                        or any(
                            keyword in tag.lower() for tag in job["tags"] for keyword in keywords
                        )
                    ]

                if filters.location:
                    filtered = [
                        job
                        for job in filtered
                        if filters.location.lower() in job["location"].lower()
                    ]

                if filters.remote_ok:
                    filtered = [job for job in filtered if job["remote"] is True]

                if filters.entry_level_only:
                    filtered = [job for job in filtered if "entry" in job["job_types"]]

                if filters.posted_within_days > 0:
                    cutoff = datetime.now() - timedelta(days=filters.posted_within_days)
                    filtered = [
                        job
                        for job in filtered
                        if datetime.fromtimestamp(job["created_at"]) > cutoff
                    ]

                for job in filtered:
                    job_result = RawJob(
                        title=job["title"],
                        company=job["company_name"],
                        location=job["location"],
                        url=job["url"],
                        source="arbeitnow",
                        description=job["description"],
                        raw_html=None,
                    )
                    result.append(job_result)

            return result
        except Exception:
            logger.exception("arbeitnow fetch failed")
            return []

    def source_name(self) -> str:
        return "arbeitnow"
