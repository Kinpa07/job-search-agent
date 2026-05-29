import hashlib

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.base import RawJob
from app.models.job import Job


class JobRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_jobs(self, jobs: list[RawJob]) -> int:

        if not jobs:
            return 0

        jobs_list = []

        for job in jobs:
            content_hash = hashlib.sha256(
                (job.title + job.company + (job.location or "")).encode("utf-8")
            ).hexdigest()

            jobs_list.append(
                {
                    "title": job.title,
                    "company": job.company,
                    "location": job.location,
                    "url": job.url,
                    "source": job.source,
                    "description": job.description,
                    "raw_html": job.raw_html,
                    "content_hash": content_hash,
                }
            )

        stmt = insert(Job).values(jobs_list).on_conflict_do_nothing(index_elements=["content_hash"])
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount  # type: ignore[attr-defined, no-any-return]

    async def get_jobs(
        self, source: str | None = None, offset: int = 0, limit: int = 100
    ) -> list[Job]:
        stmt = select(Job).order_by(Job.discovered_at.desc()).offset(offset).limit(limit)
        if source:
            stmt = stmt.where(Job.source == source)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())
