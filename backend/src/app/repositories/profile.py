from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.profile import UserProfile


class UserProfileRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_draft(self, profile: UserProfile) -> UserProfile:
        profile.status = "draft"
        await self.delete_by_status("draft")  # one draft at a time
        self.session.add(profile)
        await self.session.commit()
        await self.session.refresh(profile)
        return profile

    async def delete_by_status(self, status: str) -> None:
        """Stage deletes of every profile with this status. Does NOT commit — the
        caller's commit flushes these alongside its own changes in one transaction.

        Children are selectinload-ed so the `all, delete-orphan` cascade can issue
        their DELETEs; without them loaded the async unit of work would MissingGreenlet
        trying to lazy-load on flush (and the FK has no DB-level ON DELETE CASCADE)."""
        stmt = (
            select(UserProfile)
            .where(UserProfile.status == status)
            .options(
                selectinload(UserProfile.skills),
                selectinload(UserProfile.experiences),
                selectinload(UserProfile.educations),
            )
        )
        result = await self.session.execute(stmt)
        for profile in result.scalars():
            await self.session.delete(profile)

    async def get_draft(self) -> UserProfile | None:
        return await self._latest_by_status("draft")

    async def get_confirmed(self) -> UserProfile | None:
        return await self._latest_by_status("confirmed")

    async def get_by_id(self, profile_id: int) -> UserProfile | None:
        stmt = (
            select(UserProfile)
            .where(UserProfile.id == profile_id)
            .options(
                selectinload(UserProfile.skills),
                selectinload(UserProfile.experiences),
                selectinload(UserProfile.educations),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def delete(self, profile: UserProfile) -> None:
        await self.session.delete(profile)
        await self.session.commit()

    async def _latest_by_status(self, status: str) -> UserProfile | None:
        stmt = (
            select(UserProfile)
            .where(UserProfile.status == status)
            .order_by(UserProfile.created_at.desc())
            .options(
                selectinload(UserProfile.skills),
                selectinload(UserProfile.experiences),
                selectinload(UserProfile.educations),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def save(self, profile: UserProfile) -> None:
        await self.session.commit()
        await self.session.refresh(profile)