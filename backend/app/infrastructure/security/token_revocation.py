"""
Token revocation store using Redis.

Revoked JTIs are stored in Redis with TTL matching the token's remaining lifetime.
This allows immediate logout without waiting for token expiry.
"""

import structlog
from redis.asyncio import Redis

logger = structlog.get_logger(__name__)

REVOKED_TOKEN_PREFIX = "revoked_jti:"


class TokenRevocationStore:
    """
    Redis-backed store for revoked JWT IDs.
    A revoked JTI means the token is invalid even if the signature is valid.
    """

    def __init__(self, redis: Redis) -> None:  # type: ignore[type-arg]
        self._redis = redis

    async def revoke(self, jti: str, ttl_seconds: int) -> None:
        """
        Mark a JTI as revoked.
        TTL should equal the token's remaining lifetime so Redis
        auto-expires the entry when the token would have expired anyway.
        """
        key = f"{REVOKED_TOKEN_PREFIX}{jti}"
        await self._redis.setex(key, ttl_seconds, "1")
        logger.info("token_revoked", jti=jti, ttl_seconds=ttl_seconds)

    async def is_revoked(self, jti: str) -> bool:
        """Returns True if the JTI has been revoked."""
        key = f"{REVOKED_TOKEN_PREFIX}{jti}"
        result = await self._redis.exists(key)
        return bool(result)
