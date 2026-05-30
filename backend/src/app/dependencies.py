from collections.abc import AsyncGenerator

import redis.asyncio as aioredis

from app.config import settings


async def get_redis() -> AsyncGenerator[aioredis.Redis, None]:
    async with aioredis.Redis.from_url(settings.redis_url, decode_responses=True) as r:
        yield r
