import pytest

from app.services.rate_limiter import RateLimiter


@pytest.mark.anyio
async def test_rate_limiter_blocks_after_threshold() -> None:
    limiter = RateLimiter(max_requests=2, window_seconds=60)
    assert await limiter.allow("client:a")
    assert await limiter.allow("client:a")
    assert not await limiter.allow("client:a")
