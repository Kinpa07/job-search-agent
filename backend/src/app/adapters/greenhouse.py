from datetime import UTC, datetime, timedelta

import httpx
import structlog
from bs4 import BeautifulSoup

from app.adapters.base import JobFilters, RawJob, title_allowed

COMPANY_SLUGS = {
    "sumup": "SumUp",
    "ocadogroup": "Ocado Group",
    "sofiastars": "Sofia Stars",
    "workboard": "WorkBoard",
    "pointwild": "Point Wild",
    "conga": "Conga",
    "bettyjobboard": "Betty",
    "payhawkio": "Payhawk",
"skyscanner": "Skyscanner",
}


logger = structlog.get_logger()


class GreenhouseAdapter:
    async def fetch_jobs(self, filters: JobFilters) -> list[RawJob]:
        result = []
        async with httpx.AsyncClient() as client:
            for slug, company_name in COMPANY_SLUGS.items():
                try:
                    response = await client.get(
                        f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
                    )
                    response.raise_for_status()
                    data = response.json()["jobs"]

                    filtered = data

                    filtered = [
                        job for job in filtered if title_allowed(job["title"], filters)
                    ]

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
                            if filters.location.lower() in job["location"]["name"].lower()
                        ]

                    if filters.posted_within_days > 0:
                        cutoff = datetime.now(UTC) - timedelta(days=filters.posted_within_days)
                        filtered = [
                            job
                            for job in filtered
                            if datetime.fromisoformat(job["updated_at"]).astimezone(UTC) > cutoff
                        ]

                    for job in filtered:
                        content = job.get("content")
                        description = (
                            BeautifulSoup(content, "html.parser").get_text(
                                separator=" ", strip=True
                            )
                            if content
                            else None
                        )
                        result.append(
                            RawJob(
                                title=job["title"],
                                company=company_name,
                                location=job["location"]["name"],
                                url=job["absolute_url"],
                                source="greenhouse",
                                description=description,
                                raw_html=None,
                            )
                        )

                    logger.info("greenhouse slug fetched", slug=slug, job_count=len(filtered))

                except httpx.HTTPStatusError as e:
                    if e.response.status_code in {403, 404}:
                        logger.warning(
                            "greenhouse slug unavailable",
                            slug=slug,
                            status=e.response.status_code,
                        )
                    else:
                        logger.exception("greenhouse slug fetch failed", slug=slug)
                except Exception:
                    logger.exception("greenhouse slug fetch failed", slug=slug)

        logger.info("greenhouse fetch completed", job_count=len(result))
        return result

    def source_name(self) -> str:
        return "greenhouse"
