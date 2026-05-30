from collections.abc import AsyncGenerator

import redis.asyncio as aioredis

from app.config import settings


async def get_redis() -> AsyncGenerator[aioredis.Redis, None]:  # type: ignore[type-arg]
    async with aioredis.from_url(settings.redis_url, decode_responses=True) as r:
        yield r
