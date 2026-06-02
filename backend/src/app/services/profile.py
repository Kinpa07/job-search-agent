from datetime import date, datetime

import structlog
from dateutil import parser
from langchain_core.language_models import BaseChatModel

from app.models.profile import (
    Certification,
    Education,
    Experience,
    Language,
    Project,
    Skill,
    UserProfile,
)
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
from app.services.keyword_extractor.keyword_extractor import extract_keywords

logger = structlog.get_logger()

# projects feed the keyword extractor (their tech_stack is distinctive); certifications and
# languages are presentational and do not affect search keywords.
FIELDS_TRIGGERING_KEYWORD_EXTRACTION = {
    "summary",
    "skills",
    "experiences",
    "educations",
    "projects",
}
FIELDS_REQUIRING_WHOLESALE_REPLACEMENT = {
    "skills",
    "experiences",
    "educations",
    "projects",
    "certifications",
    "languages",
}


def parse_cv_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return parser.parse(value, default=datetime(2000, 1, 1)).date()

    except (parser.ParserError, ValueError, OverflowError):
        logger.warning("parsing date failed", value=value)
        return None


def _build_skills(items: list[SkillIn]) -> list[Skill]:
    return [
        Skill(
            name=s.name,
            proficiency_level=s.proficiency_level,
            years=s.years,
            category=s.category,
        )
        for s in items
    ]


def _build_experiences(items: list[ExperienceIn]) -> list[Experience]:
    return [
        Experience(
            company=e.company,
            title=e.title,
            location=e.location,
            start_date=parse_cv_date(e.start_date),
            end_date=parse_cv_date(e.end_date),
            bullets=[b for b in e.bullets if b.strip()],
            tech_stack=[t for t in e.tech_stack if t.strip()],
        )
        for e in items
    ]


def _build_educations(items: list[EducationIn]) -> list[Education]:
    return [
        Education(
            institution=e.institution,
            degree=e.degree,
            field=e.field,
            location=e.location,
            start_date=parse_cv_date(e.start_date),
            end_date=parse_cv_date(e.end_date),
        )
        for e in items
    ]


def _build_projects(items: list[ProjectIn]) -> list[Project]:
    return [
        Project(
            name=p.name,
            bullets=[b for b in p.bullets if b.strip()],
            tech_stack=[t for t in p.tech_stack if t.strip()],
            url=p.url,
            year=p.year,
        )
        for p in items
    ]


def _build_certifications(items: list[CertificationIn]) -> list[Certification]:
    return [Certification(name=c.name, issuer=c.issuer, year=c.year) for c in items]


def _build_languages(items: list[LanguageIn]) -> list[Language]:
    return [Language(name=lang.name, level=lang.level) for lang in items]


async def persist_confirmed(
    repo: UserProfileRepository, llm: BaseChatModel, draft: UserProfile, data: ProfileConfirmRequest
) -> UserProfile:
    draft.name = data.name
    draft.email = data.email
    draft.phone = data.phone
    draft.location = data.location
    draft.github_url = data.github_url
    draft.linkedin_url = data.linkedin_url
    draft.portfolio_url = data.portfolio_url
    draft.summary = data.summary
    draft.skills = _build_skills(data.skills)
    draft.experiences = _build_experiences(data.experiences)
    draft.educations = _build_educations(data.educations)
    draft.projects = _build_projects(data.projects)
    draft.certifications = _build_certifications(data.certifications)
    draft.languages = _build_languages(data.languages)
    await repo.delete_by_status("confirmed")  # Enforce single confirmed profile invariant
    draft.status = "confirmed"
    draft.draft_data = None  # Clear draft data to save space; it's no longer needed
    draft.search_keywords = extract_keywords(draft, llm)
    await repo.save(draft)
    logger.info("profile.confirmed", profile_id=draft.id, keywords_count=len(draft.search_keywords))
    return draft


async def update_profile(
    repo: UserProfileRepository,
    llm: BaseChatModel,
    data: ProfilePatchRequest,
    confirmed: UserProfile,
) -> UserProfile:
    fields = data.model_dump(exclude_unset=True)
    # scalars: only the ones the client sent
    for field in fields:
        if field not in FIELDS_REQUIRING_WHOLESALE_REPLACEMENT:
            setattr(confirmed, field, getattr(data, field))

    if data.skills is not None:
        confirmed.skills = _build_skills(data.skills)
    if data.experiences is not None:
        confirmed.experiences = _build_experiences(data.experiences)
    if data.educations is not None:
        confirmed.educations = _build_educations(data.educations)
    if data.projects is not None:
        confirmed.projects = _build_projects(data.projects)
    if data.certifications is not None:
        confirmed.certifications = _build_certifications(data.certifications)
    if data.languages is not None:
        confirmed.languages = _build_languages(data.languages)

    if any(field in fields for field in FIELDS_TRIGGERING_KEYWORD_EXTRACTION):
        confirmed.search_keywords = extract_keywords(confirmed, llm)
    await repo.save(confirmed)
    logger.info("profile.updated", profile_id=confirmed.id, updated_fields=list(fields.keys()))
    return confirmed
