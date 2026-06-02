from datetime import datetime, timedelta

import httpx
import structlog

from app.adapters.base import JobFilters, RawJob, keyword_matches, title_allowed

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

                filtered = [job for job in filtered if title_allowed(job["title"], filters)]

                if filters.keywords:
                    filtered = [
                        job
                        for job in filtered
                        if keyword_matches(job["title"], filters.keywords)
                        or any(keyword_matches(tag, filters.keywords) for tag in job["tags"])
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

            logger.info("remotive fetch completed", job_count=len(result))
            return result

        except httpx.HTTPError as e:
            logger.warning("remotive network error", error=str(e))
            raise

        except Exception:
            logger.exception("remotive parse error")
            return []

    def source_name(self) -> str:
        return "remotive"
