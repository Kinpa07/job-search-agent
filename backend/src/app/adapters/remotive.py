from datetime import datetime, timedelta

import httpx
import structlog

from app.adapters.base import JobFilters, RawJob

logger = structlog.get_logger()


class RemotiveAdapter:
    async def fetch_jobs(self, filters: JobFilters) -> list[RawJob]:
        result = []
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get("https://remotive.com/api/remote-jobs")
                response.raise_for_status()
                data = response.json()["jobs"]

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
                    job_filter = ["europe", "worldwide", "eu"]
                    filtered = [
                        job
                        for job in filtered
                        if filters.location.lower() in job["candidate_required_location"].lower()
                        or job["candidate_required_location"].lower() in job_filter
                    ]

                if filters.posted_within_days > 0:
                    cutoff = datetime.now() - timedelta(days=filters.posted_within_days)
                    filtered = [
                        job
                        for job in filtered
                        if datetime.fromisoformat(job["publication_date"]) > cutoff
                    ]

                for job in filtered:
                    job_result = RawJob(
                        title=job["title"],
                        company=job["company_name"],
                        location=job["candidate_required_location"],
                        url=job["url"],
                        source="remotive",
                        description=job["description"],
                        raw_html=None,
                    )
                    result.append(job_result)

            return result
        except Exception:
            logger.exception("remotive fetch failed")
            return []

    def source_name(self) -> str:
        return "remotive"
