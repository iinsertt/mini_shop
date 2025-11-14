import json
from typing import Any, Optional

import redis.asyncio as redis


class AsyncRedisCache:

    def __init__(self, redis_url: str) -> None:
        self._redis_url = redis_url
        self._redis: Optional[redis.Redis] = None

    async def init(self) -> None:
        if self._redis is None:
            self._redis = redis.from_url(
                self._redis_url,
                encoding="utf-8",
                decode_responses=True,
            )

    async def get(self, key: str) -> Optional[dict[str, Any]]:
        if self._redis is None:
            return None
        raw = await self._redis.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    async def set(self, key: str, value: dict[str, Any], ttl: Optional[int] = None) -> None:
        if self._redis is None:
            return
        data = json.dumps(value, ensure_ascii=False)
        if ttl:
            await self._redis.set(key, data, ex=ttl)
        else:
            await self._redis.set(key, data)

    async def delete(self, key: str) -> None:
        if self._redis is None:
            return
        await self._redis.delete(key)

    async def close(self) -> None:
        if self._redis is not None:
            await self._redis.close()
            self._redis = None
