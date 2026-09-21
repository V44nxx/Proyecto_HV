"""
Unit tests for the sliding-window in-memory rate limiter.
"""

import asyncio
import pytest

from app.infrastructure.security.rate_limiter import InMemoryRateLimiter


@pytest.mark.asyncio
async def test_rate_limiter_allows_under_limit():
    limiter = InMemoryRateLimiter()
    key = "test_client_1"

    # Allow 3 requests in a 60-second window
    res1 = await limiter.is_allowed(key, limit=3, window_seconds=60)
    assert res1.allowed is True
    assert res1.remaining == 2
    assert res1.retry_after == 0

    res2 = await limiter.is_allowed(key, limit=3, window_seconds=60)
    assert res2.allowed is True
    assert res2.remaining == 1

    res3 = await limiter.is_allowed(key, limit=3, window_seconds=60)
    assert res3.allowed is True
    assert res3.remaining == 0


@pytest.mark.asyncio
async def test_rate_limiter_blocks_when_exceeded():
    limiter = InMemoryRateLimiter()
    key = "test_client_blocked"

    # Consume quota of 2
    await limiter.is_allowed(key, limit=2, window_seconds=60)
    await limiter.is_allowed(key, limit=2, window_seconds=60)

    # Third request should be blocked
    blocked_res = await limiter.is_allowed(key, limit=2, window_seconds=60)
    assert blocked_res.allowed is False
    assert blocked_res.remaining == 0
    assert blocked_res.retry_after >= 1


@pytest.mark.asyncio
async def test_rate_limiter_keys_are_independent():
    limiter = InMemoryRateLimiter()
    key_a = "client_a"
    key_b = "client_b"

    # Exhaust key_a quota
    await limiter.is_allowed(key_a, limit=1, window_seconds=60)
    blocked_a = await limiter.is_allowed(key_a, limit=1, window_seconds=60)
    assert blocked_a.allowed is False

    # key_b should still be allowed
    allowed_b = await limiter.is_allowed(key_b, limit=1, window_seconds=60)
    assert allowed_b.allowed is True


@pytest.mark.asyncio
async def test_rate_limiter_reset_clears_quota():
    limiter = InMemoryRateLimiter()
    key = "reset_test"

    # Exhaust quota
    await limiter.is_allowed(key, limit=1, window_seconds=60)
    assert (await limiter.is_allowed(key, limit=1, window_seconds=60)).allowed is False

    # Reset
    await limiter.reset(key)

    # Should be allowed again
    res = await limiter.is_allowed(key, limit=1, window_seconds=60)
    assert res.allowed is True
    assert res.remaining == 0


@pytest.mark.asyncio
async def test_rate_limiter_clear_all():
    limiter = InMemoryRateLimiter()
    await limiter.is_allowed("k1", limit=1, window_seconds=60)
    await limiter.is_allowed("k2", limit=1, window_seconds=60)

    await limiter.clear_all()

    res1 = await limiter.is_allowed("k1", limit=1, window_seconds=60)
    res2 = await limiter.is_allowed("k2", limit=1, window_seconds=60)
    assert res1.allowed is True
    assert res2.allowed is True
