from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.profile import UserProfile


class UserProfileRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_draft(self, profile: UserProfile) -> UserProfile:
        profile.status = "draft"
        self.session.add(profile)
        await self.session.commit()
        await self.session.refresh(profile)
        return profile

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
