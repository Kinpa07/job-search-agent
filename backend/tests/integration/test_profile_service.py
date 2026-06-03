from datetime import date

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.profile import Skill, UserProfile
from app.repositories.profile import UserProfileRepository
from app.schemas.profile import (
    CertificationIn,
    EducationIn,
    ExperienceIn,
    LanguageIn,
    ProfileConfirmRequest,
    ProfilePatchRequest,
    ProjectIn,
    SkillIn,
)
from app.services.profile import persist_confirmed, update_profile
from tests.helpers.fakes import ToolCallingFake, tool_message

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def _cache_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "llm_cache_enabled", False)


def _keyword_llm(*keyword_sets: list[str]) -> ToolCallingFake:
    return ToolCallingFake(
        responses=[tool_message("KeywordExtractorResult", {"keywords": kw}) for kw in keyword_sets]
    )


def _confirm_request(name: str = "Veselin") -> ProfileConfirmRequest:
    return ProfileConfirmRequest(
        name=name,
        email="v@example.com",
        location="Sofia",
        github_url="https://github.com/kinpa07",
        linkedin_url="https://www.linkedin.com/in/x",
        summary="Engineer",
        skills=[SkillIn(name="Python", category="Languages", proficiency_level="proficient")],
        experiences=[
            ExperienceIn(
                company="Quickbase",
                title="Intern",
                location="Sofia",
                start_date="11/2025",
                end_date="05/2026",
                bullets=["did x"],
                tech_stack=["Python"],
            )
        ],
        educations=[
            EducationIn(
                institution="NBU",
                degree="Bachelor",
                field="Informatics",
                location="Sofia",
                start_date="10/2021",
                end_date="2026",
            )
        ],
        projects=[
            ProjectIn(name="OrderFlow", bullets=["built x"], tech_stack=["Redis"], year=2026)
        ],
        certifications=[CertificationIn(name="AWS SAA", issuer="Amazon", year=2024)],
        languages=[LanguageIn(name="English", level="C1")],
    )


async def _count(session: AsyncSession, model: type) -> int:
    result = await session.execute(select(func.count()).select_from(model))
    return int(result.scalar_one())


async def test_persist_confirmed_materializes_children_and_parses_dates(
    db_session: AsyncSession,
) -> None:
    repo = UserProfileRepository(db_session)
    await repo.create_draft(UserProfile(draft_data={"raw": "x"}))
    draft = await repo.get_draft()  # selectinloaded, as the confirm endpoint passes it
    assert draft is not None

    await persist_confirmed(repo, _keyword_llm(["Backend Engineer"]), draft, _confirm_request())
    profile = await repo.get_confirmed()
    assert profile is not None

    assert profile.status == "confirmed"
    assert profile.draft_data is None  # cleared to SQL NULL on confirm
    assert profile.search_keywords == ["Backend Engineer"]
    assert profile.github_url == "https://github.com/kinpa07"
    assert profile.skills[0].category == "Languages"
    assert profile.experiences[0].start_date == date(2025, 11, 1)  # free-text → real date
    assert profile.educations[0].end_date == date(2026, 1, 1)
    assert [p.name for p in profile.projects] == ["OrderFlow"]
    assert [c.name for c in profile.certifications] == ["AWS SAA"]
    assert [lang.level for lang in profile.languages] == ["C1"]


async def test_persist_confirmed_replaces_prior_confirmed(db_session: AsyncSession) -> None:
    repo = UserProfileRepository(db_session)
    llm = _keyword_llm(["A"], ["B"])

    await repo.create_draft(UserProfile(draft_data={"n": 1}))
    d1 = await repo.get_draft()
    assert d1 is not None
    await persist_confirmed(repo, llm, d1, _confirm_request(name="First"))
    await repo.create_draft(UserProfile(draft_data={"n": 2}))
    d2 = await repo.get_draft()
    assert d2 is not None
    await persist_confirmed(repo, llm, d2, _confirm_request(name="Second"))

    confirmed = await repo.get_confirmed()
    assert confirmed is not None and confirmed.name == "Second"
    # Exactly one confirmed profile remains — the prior one was deleted.
    statuses = (await db_session.execute(select(UserProfile.status))).scalars().all()
    assert statuses == ["confirmed"]


async def test_update_profile_scalar_does_not_reextract_keywords(db_session: AsyncSession) -> None:
    repo = UserProfileRepository(db_session)
    llm = _keyword_llm(["initial"], ["after"])  # second only consumed if re-extraction runs
    await repo.create_draft(UserProfile(draft_data={}))
    draft = await repo.get_draft()
    assert draft is not None
    await persist_confirmed(repo, llm, draft, _confirm_request())
    confirmed = await repo.get_confirmed()
    assert confirmed is not None

    updated = await update_profile(repo, llm, ProfilePatchRequest(phone="999"), confirmed)

    assert updated.phone == "999"
    assert updated.search_keywords == ["initial"]  # phone is not a keyword-affecting field


async def test_update_profile_replaces_children_and_reextracts(db_session: AsyncSession) -> None:
    repo = UserProfileRepository(db_session)
    llm = _keyword_llm(["initial"], ["after"])
    await repo.create_draft(UserProfile(draft_data={}))
    draft = await repo.get_draft()
    assert draft is not None
    await persist_confirmed(repo, llm, draft, _confirm_request())
    confirmed = await repo.get_confirmed()
    assert confirmed is not None

    updated = await update_profile(
        repo, llm, ProfilePatchRequest(skills=[SkillIn(name="Go")]), confirmed
    )

    assert [s.name for s in updated.skills] == ["Go"]
    assert updated.search_keywords == ["after"]  # skills change triggers re-extraction
    assert await _count(db_session, Skill) == 1  # old skill replaced, not accumulated
