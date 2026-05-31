"""Record/replay helper for LLM development iteration (Standing Rule 6).

Not for unit tests — those use ``FakeMessagesListChatModel`` (see ``conftest.fake_llm``).
This makes one real API call, caches the response to ``tests/fixtures/llm_responses/``,
and replays it on every subsequent run so iterating on response-parsing code costs nothing.
"""

import json
from pathlib import Path
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "llm_responses"


def load_or_call(
    fixture_name: str,
    llm: BaseChatModel,
    messages: list[BaseMessage],
    force_refresh: bool = False,
) -> AIMessage:
    """Load a cached LLM response, or make a real call and cache it.

    Args:
        fixture_name: Base name of the JSON fixture (no extension).
        llm: A real chat model — only invoked on a cache miss or ``force_refresh``.
        messages: The prompt to send on a real call.
        force_refresh: Bypass the cache and overwrite the fixture with a fresh call.
    """
    fixture_path = FIXTURES_DIR / f"{fixture_name}.json"
    if fixture_path.exists() and not force_refresh:
        with fixture_path.open() as f:
            data: dict[str, Any] = json.load(f)
        return AIMessage(**data)

    # Real call — costs money, only happens once per fixture (or on force_refresh).
    result = llm.invoke(messages)
    fixture_path.parent.mkdir(parents=True, exist_ok=True)
    with fixture_path.open("w") as f:
        json.dump(
            {"content": result.content, "tool_calls": result.tool_calls},
            f,
            indent=2,
            default=str,
        )
    return result
