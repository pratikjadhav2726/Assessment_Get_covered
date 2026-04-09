from redis.asyncio import Redis

from app.services.ports import RateLimiterPort


class RedisRateLimiter(RateLimiterPort):
    def __init__(self, redis: Redis, max_requests: int, window_seconds: int) -> None:
        self._redis = redis
        self._max_requests = max_requests
        self._window_seconds = window_seconds

    async def allow(self, key: str) -> bool:
        redis_key = f"rate_limit:{key}"
        current = await self._redis.incr(redis_key)
        if current == 1:
            await self._redis.expire(redis_key, self._window_seconds)
        return current <= self._max_requests
