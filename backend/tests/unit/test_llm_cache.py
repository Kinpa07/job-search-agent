from pathlib import Path
from typing import Any

import pytest
from langchain_community.chat_models.fake import FakeMessagesListChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.runnables import Runnable
from pydantic import BaseModel

from app.config import settings
from app.llm_cache import invoke_tool


class DummyTool(BaseModel):
    value: str


class ToolCallFake(FakeMessagesListChatModel):
    """A fake that supports ``bind_tools`` (the base raises) by returning itself and ignoring
    the tools — the seeded AIMessages already carry the ``tool_calls`` invoke_tool reads."""

    def bind_tools(self, tools: Any, **kwargs: Any) -> Runnable[Any, Any]:
        return self


def _ai(value: str) -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[
            {"name": "DummyTool", "args": {"value": value}, "id": "1", "type": "tool_call"}
        ],
    )


@pytest.fixture(autouse=True)
def _isolated_cache_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # Each test gets a fresh, throwaway cache dir so fixtures don't leak between tests.
    monkeypatch.setattr("app.llm_cache.CACHE_DIR", tmp_path)


def test_replays_identical_request(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "llm_cache_enabled", True)
    fake = ToolCallFake(responses=[_ai("first"), _ai("second")])
    messages: list[BaseMessage] = [HumanMessage(content="same input")]

    first = invoke_tool(fake, DummyTool, messages)
    second = invoke_tool(fake, DummyTool, messages)

    # The second call is a cache hit: it returns the FIRST response, not the fake's
    # advanced "second" — proving the model was not called again.
    assert first.tool_calls[0]["args"] == {"value": "first"}
    assert second.tool_calls[0]["args"] == {"value": "first"}


def test_disabled_flag_calls_through_every_time(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "llm_cache_enabled", False)
    fake = ToolCallFake(responses=[_ai("first"), _ai("second")])
    messages: list[BaseMessage] = [HumanMessage(content="same input")]

    first = invoke_tool(fake, DummyTool, messages)
    second = invoke_tool(fake, DummyTool, messages)

    # No caching — the fake advances, so the two calls return different responses.
    assert first.tool_calls[0]["args"] == {"value": "first"}
    assert second.tool_calls[0]["args"] == {"value": "second"}


def test_different_input_is_a_cache_miss(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "llm_cache_enabled", True)
    fake = ToolCallFake(responses=[_ai("first"), _ai("second")])
    input_a: list[BaseMessage] = [HumanMessage(content="input A")]
    input_b: list[BaseMessage] = [HumanMessage(content="input B")]

    first = invoke_tool(fake, DummyTool, input_a)
    second = invoke_tool(fake, DummyTool, input_b)

    # Different message content → different cache key → a real call both times.
    assert first.tool_calls[0]["args"] == {"value": "first"}
    assert second.tool_calls[0]["args"] == {"value": "second"}
