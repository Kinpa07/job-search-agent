import pytest
from langchain_core.messages import AIMessage

from app.config import settings
from app.models.profile import Experience, Project, Skill, UserProfile
from app.services.keyword_extractor.keyword_extractor import extract_keywords
from tests.helpers.fakes import ToolCallingFake, tool_message


@pytest.fixture(autouse=True)
def _cache_off(monkeypatch: pytest.MonkeyPatch) -> None:
    # Force the real (fake) call path, not the disk cache, so results are deterministic.
    monkeypatch.setattr(settings, "llm_cache_enabled", False)


def _profile() -> UserProfile:
    return UserProfile(
        summary="Full-stack engineer",
        skills=[Skill(name="Python"), Skill(name="FastAPI")],
        experiences=[Experience(title="Backend Intern", tech_stack=["FastAPI"], bullets=["b"])],
        projects=[Project(name="OrderFlow", tech_stack=["Redis"], bullets=["b"])],
    )


def test_returns_keywords_from_tool_call() -> None:
    fake = ToolCallingFake(
        responses=[
            tool_message("KeywordExtractorResult", {"keywords": ["Backend Engineer", "Redis"]})
        ]
    )
    assert extract_keywords(_profile(), fake) == ["Backend Engineer", "Redis"]


def test_raises_when_model_returns_no_tool_call() -> None:
    fake = ToolCallingFake(responses=[AIMessage(content="I refuse to call the tool")])
    with pytest.raises(ValueError, match="tool call"):
        extract_keywords(_profile(), fake)
