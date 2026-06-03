from collections.abc import AsyncGenerator

import redis.asyncio as aioredis
from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel

from app.config import settings


async def get_redis() -> AsyncGenerator[aioredis.Redis, None]:
    async with aioredis.Redis.from_url(settings.redis_url, decode_responses=True) as r:
        yield r


def get_llm() -> BaseChatModel:
    return init_chat_model(
        settings.anthropic_model,
        model_provider="anthropic",
        api_key=settings.anthropic_api_key,
        temperature=0.0,
        max_tokens=4096,
        timeout=60.0,
    )
