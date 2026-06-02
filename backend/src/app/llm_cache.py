"""Dev-only record/replay cache for tool-calling LLM invocations (Standing Rule 6).

A single ``upload-cv`` is two real Anthropic calls (extraction + keyword extraction). While
iterating on code *around* the LLM against a stable profile, paying for the same response each
run is waste. ``invoke_tool`` forces a single-tool call and, when ``settings.llm_cache_enabled``,
replays a cached response for an identical request — keyed by a hash of the model, the tool's
JSON schema, and the message contents, so changing the prompt, the input, the tool schema, or
the model all correctly invalidate the cache. Off by default; real calls run normally.

Not for unit tests — those use ``FakeMessagesListChatModel`` (see ``conftest.fake_llm``).
"""

import hashlib
import json
from pathlib import Path
from typing import Any

import structlog
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from pydantic import BaseModel

from app.config import settings

logger = structlog.get_logger()

CACHE_DIR = Path(__file__).resolve().parent.parent.parent / ".llm_cache"


def _cache_key(tool: type[BaseModel], messages: list[BaseMessage]) -> str:
    payload = json.dumps(
        {
            "model": settings.anthropic_model,
            "tool": tool.__name__,
            "schema": tool.model_json_schema(),
            "messages": [{"type": m.type, "content": m.content} for m in messages],
        },
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def _call(llm: BaseChatModel, tool: type[BaseModel], messages: list[BaseMessage]) -> AIMessage:
    result = llm.bind_tools([tool], tool_choice=tool.__name__).invoke(messages)
    if not isinstance(result, AIMessage):
        raise TypeError(f"Expected AIMessage from tool call, got {type(result).__name__}")
    return result


def invoke_tool(
    llm: BaseChatModel, tool: type[BaseModel], messages: list[BaseMessage]
) -> AIMessage:
    """Force ``llm`` to call ``tool`` and return the resulting message. With caching enabled,
    replay an identical prior request from disk; otherwise (or on a miss) call and store it."""
    if not settings.llm_cache_enabled:
        return _call(llm, tool, messages)

    path = CACHE_DIR / f"{tool.__name__}_{_cache_key(tool, messages)}.json"
    if path.exists():
        data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        logger.info("llm_cache.hit", tool=tool.__name__, fixture=path.name)
        return AIMessage(content=data["content"], tool_calls=data["tool_calls"])

    result = _call(llm, tool, messages)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {"content": result.content, "tool_calls": result.tool_calls},
            default=str,
            indent=2,
        ),
        encoding="utf-8",
    )
    logger.info("llm_cache.miss_stored", tool=tool.__name__, fixture=path.name)
    return result
