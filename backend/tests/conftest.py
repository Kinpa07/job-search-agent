from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from langchain_community.chat_models.fake import FakeMessagesListChatModel
from langchain_core.messages import AIMessage

from app.main import app


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
def fake_llm() -> FakeMessagesListChatModel:
    """A deterministic LLM substitute for unit tests (Standing Rule 6).

    Returns pre-configured responses with no API call. Override the responses
    per test by constructing your own ``FakeMessagesListChatModel(responses=[...])``
    when you need tool-call output or a specific payload.
    """
    return FakeMessagesListChatModel(
        responses=[AIMessage(content="default fake response")]
    )
