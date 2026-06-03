"""Shared test doubles for LLM-calling code (Standing Rule 6 — no real API in unit tests)."""

from typing import Any

from langchain_community.chat_models.fake import FakeMessagesListChatModel
from langchain_core.messages import AIMessage
from langchain_core.runnables import Runnable


class ToolCallingFake(FakeMessagesListChatModel):
    """A fake chat model that supports ``bind_tools`` (the base implementation raises) by
    returning itself and ignoring the tools, so code using ``llm.bind_tools(...).invoke(...)``
    works in tests. Seed it with ``tool_message(...)`` responses that carry the tool call."""

    def bind_tools(self, tools: Any, **kwargs: Any) -> Runnable[Any, Any]:
        return self


def tool_message(tool_name: str, args: dict[str, Any]) -> AIMessage:
    """An AIMessage shaped like a forced tool call, for seeding ``ToolCallingFake``."""
    return AIMessage(
        content="",
        tool_calls=[{"name": tool_name, "args": args, "id": "1", "type": "tool_call"}],
    )
