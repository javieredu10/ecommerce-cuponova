import os
from typing import Optional
import redis.asyncio as aioredis
from src.domain.ports.repositories import ITokenCache

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


class RedisTokenCache(ITokenCache):
    def __init__(self, client: aioredis.Redis):
        self._client = client

    async def set_refresh_token(self, user_id: str, token: str, ttl_seconds: int) -> None:
        await self._client.setex(f"refresh:{user_id}", ttl_seconds, token)

    async def get_refresh_token(self, user_id: str) -> Optional[str]:
        val = await self._client.get(f"refresh:{user_id}")
        return val.decode() if val else None

    async def revoke_refresh_token(self, user_id: str) -> None:
        await self._client.delete(f"refresh:{user_id}")


async def get_redis() -> aioredis.Redis:
    return aioredis.from_url(REDIS_URL, decode_responses=False)
