"""
In-memory sliding-window rate limiter for API endpoints.

Tracks request timestamps per client/key within a sliding window.
Provides thread-safe operations, automatic eviction of stale entries,
and accurate Retry-After calculation.
"""

import asyncio
import time
from collections import defaultdict
from dataclasses import dataclass


@dataclass
class RateLimitResult:
    """Outcome of a rate limit check."""
    allowed: bool
    limit: int
    remaining: int
    retry_after: int  # Seconds until next request is allowed


class InMemoryRateLimiter:
    """
    Sliding-window rate limiter.
    Stores monotonically increasing timestamps for each key.
    """

    def __init__(self) -> None:
        self._records: dict[str, list[float]] = defaultdict(list)
        self._lock = asyncio.Lock()
        self._last_cleanup = time.time()

    async def is_allowed(
        self,
        key: str,
        limit: int,
        window_seconds: int = 60,
    ) -> RateLimitResult:
        """
        Determines whether an action associated with `key` is permitted.

        Args:
            key: Client identifier (IP, user ID, or composite route:client).
            limit: Maximum allowed requests within window_seconds.
            window_seconds: Window duration in seconds (default: 60).

        Returns:
            RateLimitResult indicating allowed status, remaining quota, and retry_after.
        """
        async with self._lock:
            now = time.time()
            cutoff = now - window_seconds

            # Cleanup expired timestamps for this key
            timestamps = [t for t in self._records[key] if t > cutoff]
            self._records[key] = timestamps

            # Periodic general cleanup every 5 minutes to prevent memory leak
            if now - self._last_cleanup > 300:
                self._cleanup_all(cutoff)
                self._last_cleanup = now

            count = len(timestamps)

            if count < limit:
                # Quota available: record this request
                timestamps.append(now)
                remaining = limit - count - 1
                return RateLimitResult(
                    allowed=True,
                    limit=limit,
                    remaining=remaining,
                    retry_after=0,
                )
            else:
                # Limit exceeded: calculate retry-after based on oldest timestamp in window
                oldest_in_window = timestamps[0]
                retry_after = max(1, int(oldest_in_window + window_seconds - now) + 1)
                return RateLimitResult(
                    allowed=False,
                    limit=limit,
                    remaining=0,
                    retry_after=retry_after,
                )

    async def reset(self, key: str) -> None:
        """Clears all recorded timestamps for a specific key."""
        async with self._lock:
            self._records.pop(key, None)

    async def clear_all(self) -> None:
        """Clears all recorded rate limits across all keys."""
        async with self._lock:
            self._records.clear()

    def _cleanup_all(self, cutoff: float) -> None:
        """Removes expired entries across all keys."""
        keys_to_remove = []
        for k, v in self._records.items():
            valid = [t for t in v if t > cutoff]
            if valid:
                self._records[k] = valid
            else:
                keys_to_remove.append(k)
        for k in keys_to_remove:
            del self._records[k]


# Global singleton instance
rate_limiter = InMemoryRateLimiter()
