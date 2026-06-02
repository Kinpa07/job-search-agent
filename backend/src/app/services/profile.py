from datetime import date, datetime

import structlog
from dateutil import parser
from langchain_core.language_models import BaseChatModel

from app.models.profile import Education, Experience, Skill, UserProfile
from app.repositories.profile import UserProfileRepository
from app.schemas.profile import ProfileConfirmRequest, ProfilePatchRequest
from app.services.keyword_extractor.keyword_extractor import extract_keywords

logger = structlog.get_logger()

FIELDS_TRIGGERING_KEYWORD_EXTRACTION = {"summary", "skills", "experiences", "educations"}
FIELDS_REQUIRING_WHOLESALE_REPLACEMENT = {"skills", "experiences", "educations"}


def parse_cv_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return parser.parse(value, default=datetime(2000, 1, 1)).date()

    except (parser.ParserError, ValueError, OverflowError):
        logger.warning("parsing date failed", value=value)
        return None


async def persist_confirmed(
    repo: UserProfileRepository, llm: BaseChatModel, draft: UserProfile, data: ProfileConfirmRequest
) -> UserProfile:
    draft.name = data.name
    draft.email = data.email
    draft.phone = data.phone
    draft.location = data.location
    draft.summary = data.summary
    draft.skills = [
        Skill(name=s.name, proficiency_level=s.proficiency_level, years=s.years)
        for s in data.skills
    ]
    draft.experiences = [
        Experience(
            company=e.company,
            title=e.title,
            start_date=parse_cv_date(e.start_date),
            end_date=parse_cv_date(e.end_date),
            bullets=[b for b in e.bullets if b.strip()],
            tech_stack=[t for t in e.tech_stack if t.strip()],
        )
        for e in data.experiences
    ]

    draft.educations = [
        Education(
            institution=e.institution,
            degree=e.degree,
            field=e.field,
            year=e.year,
        )
        for e in data.educations
    ]
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
        confirmed.skills = [
            Skill(name=s.name, proficiency_level=s.proficiency_level, years=s.years)
            for s in data.skills
        ]
    if data.experiences is not None:
        confirmed.experiences = [
            Experience(
                company=e.company,
                title=e.title,
                start_date=parse_cv_date(e.start_date),
                end_date=parse_cv_date(e.end_date),
                bullets=[b for b in e.bullets if b.strip()],
                tech_stack=[t for t in e.tech_stack if t.strip()],
            )
            for e in data.experiences
        ]
    if data.educations is not None:
        confirmed.educations = [
            Education(
                institution=e.institution,
                degree=e.degree,
                field=e.field,
                year=e.year,
            )
            for e in data.educations
        ]

    if any(field in fields for field in FIELDS_TRIGGERING_KEYWORD_EXTRACTION):
        confirmed.search_keywords = extract_keywords(confirmed, llm)
    await repo.save(confirmed)
    logger.info("profile.updated", profile_id=confirmed.id, updated_fields=list(fields.keys()))
    return confirmed
