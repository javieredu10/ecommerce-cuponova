import os
import json
import logging
from typing import Optional, List
import redis.asyncio as aioredis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/3")
CACHE_TTL = 300  # 5 minutos
logger = logging.getLogger(__name__)

_redis: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(REDIS_URL, decode_responses=True)
    return _redis


class ProductCache:
    """Cache Redis para productos — evita lecturas repetidas a Postgres."""

    def __init__(self, client: aioredis.Redis):
        self._r = client

    def _key(self, tenant_id: str, product_id: str) -> str:
        return f"product:{tenant_id}:{product_id}"

    def _list_key(self, tenant_id: str, product_type: str = "all") -> str:
        return f"products:{tenant_id}:{product_type}"

    async def get(self, tenant_id: str, product_id: str) -> Optional[dict]:
        try:
            data = await self._r.get(self._key(tenant_id, product_id))
            return json.loads(data) if data else None
        except Exception as e:
            logger.warning("Cache get error: %s", e)
            return None

    async def set(self, tenant_id: str, product_id: str, data: dict) -> None:
        try:
            await self._r.setex(
                self._key(tenant_id, product_id),
                CACHE_TTL,
                json.dumps(data, default=str),
            )
        except Exception as e:
            logger.warning("Cache set error: %s", e)

    async def invalidate(self, tenant_id: str, product_id: str) -> None:
        try:
            await self._r.delete(self._key(tenant_id, product_id))
            # Invalidar listas también
            async for key in self._r.scan_iter(f"products:{tenant_id}:*"):
                await self._r.delete(key)
        except Exception as e:
            logger.warning("Cache invalidate error: %s", e)

    async def get_list(self, tenant_id: str, product_type: str = "all") -> Optional[List[dict]]:
        try:
            data = await self._r.get(self._list_key(tenant_id, product_type))
            return json.loads(data) if data else None
        except Exception:
            return None

    async def set_list(self, tenant_id: str, data: List[dict], product_type: str = "all") -> None:
        try:
            await self._r.setex(
                self._list_key(tenant_id, product_type),
                CACHE_TTL,
                json.dumps(data, default=str),
            )
        except Exception as e:
            logger.warning("Cache set_list error: %s", e)
