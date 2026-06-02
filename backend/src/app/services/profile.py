from datetime import date, datetime

import structlog
from dateutil import parser
from langchain_core.language_models import BaseChatModel

from app.models.profile import Education, Experience, Skill, UserProfile
from app.repositories.profile import UserProfileRepository
from app.schemas.profile import ProfileConfirmRequest
from app.services.keyword_extractor.keyword_extractor import extract_keywords

logger = structlog.get_logger()


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
