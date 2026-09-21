"""
Use case: Refresh access token

Validates the refresh token, checks it hasn't been revoked,
issues a new access token (and optionally rotates the refresh token).

Token rotation is a security best practice: each refresh token is
single-use, preventing replay attacks.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime

import structlog

from app.infrastructure.database.repositories.user_repository import UserRepository
from app.infrastructure.security.jwt_handler import JWTHandler, TokenError, TokenExpiredError
from app.infrastructure.security.token_revocation import TokenRevocationStore

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class RefreshResult:
    access_token: str
    access_jti: str
    access_expires_at: datetime
    new_refresh_token: str | None
    new_refresh_jti: str | None
    new_refresh_expires_at: datetime | None


class RefreshTokenUseCase:
    """
    Issues a new access token given a valid refresh token.
    Implements refresh token rotation for security.
    """

    def __init__(
        self,
        user_repo: UserRepository,
        jwt_handler: JWTHandler,
        revocation_store: TokenRevocationStore,
        rotate_refresh: bool = True,
    ) -> None:
        self._user_repo = user_repo
        self._jwt = jwt_handler
        self._revocation = revocation_store
        self._rotate = rotate_refresh

    async def execute(self, refresh_token: str) -> RefreshResult:
        from app.application.use_cases.auth.exceptions import AuthenticationError

        # Decode and validate
        try:
            payload = self._jwt.decode_refresh_token(refresh_token)
        except TokenExpiredError:
            raise AuthenticationError("Refresh token expirado. Inicie sesión nuevamente.")
        except TokenError as exc:
            raise AuthenticationError(f"Token inválido: {exc.message}")

        jti = payload.get("jti")
        user_id_str = payload.get("sub")

        if not jti or not user_id_str:
            raise AuthenticationError("Token malformado")

        # Check revocation
        if await self._revocation.is_revoked(jti):
            logger.warning("refresh_token_already_revoked", jti=jti)
            raise AuthenticationError("Token de actualización ya fue utilizado o revocado.")

        # Verify user still active
        user = await self._user_repo.get_by_id(uuid.UUID(user_id_str))
        if not user or not user.is_active:
            raise AuthenticationError("Cuenta no disponible")

        # Get current permissions (may have changed since login)
        permissions = await self._user_repo.get_user_permissions(user.id)
        role_name = user.role.name if user.role else "CONSULTOR"

        # Issue new access token
        access_token, access_jti, access_expires = self._jwt.create_access_token(
            user_id=user_id_str,
            role=role_name,
            permissions=permissions,
        )

        # Rotate refresh token (revoke old, issue new)
        new_refresh_token = None
        new_refresh_jti = None
        new_refresh_expires = None

        if self._rotate:
            from datetime import timezone
            exp_timestamp = payload.get("exp", 0)
            from datetime import datetime
            old_expires = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
            from datetime import timezone as tz_mod
            from datetime import datetime as dt_mod
            now = dt_mod.now(tz=tz_mod.utc)
            ttl = max(0, int((old_expires - now).total_seconds()))
            await self._revocation.revoke(jti, ttl)

            new_refresh_token, new_refresh_jti, new_refresh_expires = (
                self._jwt.create_refresh_token(user_id=user_id_str)
            )

        logger.info("token_refreshed", user_id=user_id_str)

        return RefreshResult(
            access_token=access_token,
            access_jti=access_jti,
            access_expires_at=access_expires,
            new_refresh_token=new_refresh_token,
            new_refresh_jti=new_refresh_jti,
            new_refresh_expires_at=new_refresh_expires,
        )
