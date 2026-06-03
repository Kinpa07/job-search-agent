import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profile import Skill, UserProfile
from app.repositories.profile import UserProfileRepository

pytestmark = pytest.mark.integration


async def _count(session: AsyncSession, model: type) -> int:
    result = await session.execute(select(func.count()).select_from(model))
    return int(result.scalar_one())


async def test_create_draft_inserts_and_is_returned(db_session: AsyncSession) -> None:
    repo = UserProfileRepository(db_session)
    await repo.create_draft(UserProfile(draft_data={"name": "A"}, skills=[Skill(name="Python")]))

    draft = await repo.get_draft()
    assert draft is not None
    assert draft.status == "draft"
    assert [s.name for s in draft.skills] == ["Python"]


async def test_create_draft_replaces_prior_draft(db_session: AsyncSession) -> None:
    repo = UserProfileRepository(db_session)
    await repo.create_draft(UserProfile(draft_data={"n": "first"}, skills=[Skill(name="Old")]))
    await repo.create_draft(UserProfile(draft_data={"n": "second"}, skills=[Skill(name="New")]))

    # Single-draft invariant: only the latest draft and its children survive.
    assert await _count(db_session, UserProfile) == 1
    assert await _count(db_session, Skill) == 1
    draft = await repo.get_draft()
    assert draft is not None and draft.draft_data == {"n": "second"}


async def test_delete_by_status_cascades_to_children(db_session: AsyncSession) -> None:
    repo = UserProfileRepository(db_session)
    db_session.add(
        UserProfile(name="C", status="confirmed", skills=[Skill(name="X"), Skill(name="Y")])
    )
    await db_session.commit()

    await repo.delete_by_status("confirmed")
    await db_session.commit()  # delete_by_status is stage-only

    assert await _count(db_session, UserProfile) == 0
    assert await _count(db_session, Skill) == 0  # delete-orphan cascade fired


async def test_get_confirmed_ignores_drafts(db_session: AsyncSession) -> None:
    repo = UserProfileRepository(db_session)
    await repo.create_draft(UserProfile(draft_data={"x": 1}))
    db_session.add(UserProfile(name="Conf", status="confirmed"))
    await db_session.commit()

    confirmed = await repo.get_confirmed()
    assert confirmed is not None
    assert confirmed.status == "confirmed" and confirmed.name == "Conf"
