import json

import structlog
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from app.models import UserProfile
from app.services.keyword_extractor.prompts import PROMPT

logger = structlog.get_logger()


class KeywordExtractorResult(BaseModel):
    keywords: list[str]


def extract_keywords(profile: UserProfile, llm: BaseChatModel) -> list[str]:
    profile_summary = {
        "summary": profile.summary,
        "skills": [s.name for s in profile.skills],
        "experiences": [
            {"title": e.title, "tech_stack": e.tech_stack, "bullets": e.bullets}
            for e in profile.experiences
        ],
        "projects": [
            {"name": p.name, "tech_stack": p.tech_stack, "bullets": p.bullets}
            for p in profile.projects
        ],
    }

    result = llm.bind_tools([KeywordExtractorResult], tool_choice="KeywordExtractorResult").invoke(
        [
            SystemMessage(content=PROMPT),
            HumanMessage(content=json.dumps(profile_summary)),
        ],
    )
    if not result.tool_calls:
        raise ValueError("LLM did not return any tool calls. Unable to extract keywords.")
    extracted = KeywordExtractorResult.model_validate(result.tool_calls[0]["args"])
    logger.info("keyword_extraction.done", extracted_keywords=extracted.keywords)
    return extracted.keywords
