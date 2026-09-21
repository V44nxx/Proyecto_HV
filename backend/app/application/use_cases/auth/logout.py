"""
Use case: Logout

Revokes both the access token and the refresh token by storing
their JTIs in Redis. After logout, neither token can be used again
even if they haven't expired yet.
"""

from dataclasses import dataclass
from datetime import datetime, timezone

import structlog

from app.config.constants import AuditAction
from app.infrastructure.database.repositories.user_repository import UserRepository
from app.infrastructure.security.token_revocation import TokenRevocationStore

logger = structlog.get_logger(__name__)


class LogoutUseCase:
    """
    Invalidates the user's current tokens.

    Both the access JTI and refresh JTI are stored in Redis with TTLs
    matching their remaining validity, so they are automatically cleaned
    up when they would have expired anyway.
    """

    def __init__(
        self,
        user_repo: UserRepository,
        revocation_store: TokenRevocationStore,
    ) -> None:
        self._user_repo = user_repo
        self._revocation = revocation_store

    async def execute(
        self,
        user_id: str,
        access_jti: str,
        access_expires_at: datetime,
        refresh_jti: str | None = None,
        refresh_expires_at: datetime | None = None,
        ip_address: str | None = None,
    ) -> None:
        now = datetime.now(tz=timezone.utc)

        # Revoke access token
        access_ttl = max(0, int((access_expires_at - now).total_seconds()))
        await self._revocation.revoke(access_jti, access_ttl)

        # Revoke refresh token if provided
        if refresh_jti and refresh_expires_at:
            refresh_ttl = max(0, int((refresh_expires_at - now).total_seconds()))
            await self._revocation.revoke(refresh_jti, refresh_ttl)

        # Audit log
        import uuid
        await self._user_repo.create_audit_log(
            action=AuditAction.LOGOUT,
            user_id=uuid.UUID(user_id),
            ip_address=ip_address,
        )
        logger.info("logout_success", user_id=user_id)
