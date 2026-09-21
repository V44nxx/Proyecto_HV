"""
Use case: Login

Responsibilities:
- Validate email existence
- Check account status (active, not locked)
- Verify password
- Handle failed attempts and progressive lockout
- Issue access + refresh tokens
- Write audit log
- Return token pair

This class does NOT know about HTTP.
It does NOT know about FastAPI.
It receives what it needs and returns a result object.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import structlog

from app.config.constants import AuditAction
from app.config.settings import get_settings
from app.infrastructure.database.repositories.user_repository import UserRepository
from app.infrastructure.security.jwt_handler import JWTHandler
from app.infrastructure.security.password_hasher import PasswordHasher

logger = structlog.get_logger(__name__)
_settings = get_settings()

# Progressive lockout durations (minutes) indexed by attempt thresholds
LOCKOUT_SCHEDULE = [
    (5, 5),    # >= 5 attempts → lock for 5 min
    (8, 15),   # >= 8 attempts → lock for 15 min
    (10, 60),  # >= 10 attempts → lock for 60 min
]


@dataclass(frozen=True)
class LoginResult:
    access_token: str
    refresh_token: str
    access_jti: str
    refresh_jti: str
    access_expires_at: datetime
    refresh_expires_at: datetime
    user_id: str
    user_email: str
    user_full_name: str
    role_name: str
    permissions: list[str]


class LoginUseCase:
    """
    Authenticates a user with email + password.

    Design notes:
    - Never reveals whether email or password is wrong (uniform error message)
    - Progressive lockout: 5/8/10 failures → 5/15/60 min lockout
    - Rehashes password if Argon2 parameters have changed
    - Audit-logs both success and failure
    """

    def __init__(
        self,
        user_repo: UserRepository,
        hasher: PasswordHasher,
        jwt_handler: JWTHandler,
    ) -> None:
        self._user_repo = user_repo
        self._hasher = hasher
        self._jwt = jwt_handler

    async def execute(
        self,
        email: str,
        password: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> LoginResult:
        """
        Authenticate user.

        Raises:
            AuthenticationError: if credentials are wrong, account is inactive,
                                  or account is locked.
        """
        from app.application.use_cases.auth.exceptions import AuthenticationError

        user = await self._user_repo.get_by_email(email)

        # --- Step 1: User existence check ---
        # Intentionally vague error — don't reveal if email exists
        if user is None:
            logger.warning("login_user_not_found", email=email, ip=ip_address)
            raise AuthenticationError("Credenciales incorrectas")

        # --- Step 2: Account active check ---
        if not user.is_active:
            logger.warning("login_inactive_account", user_id=str(user.id))
            raise AuthenticationError("Cuenta desactivada. Contacte al administrador.")

        # --- Step 3: Lockout check ---
        if user.locked_until and user.locked_until > datetime.now(tz=timezone.utc):
            remaining = int((user.locked_until - datetime.now(tz=timezone.utc)).total_seconds() / 60) + 1
            logger.warning("login_account_locked", user_id=str(user.id))
            await self._user_repo.create_audit_log(
                action=AuditAction.FAILED_LOGIN,
                user_id=user.id,
                ip_address=ip_address,
                details={"reason": "account_locked"},
            )
            raise AuthenticationError(
                f"Cuenta bloqueada. Intente de nuevo en {remaining} minuto(s)."
            )

        # --- Step 4: Password verification ---
        if not self._hasher.verify(user.hashed_password, password):
            new_count = await self._user_repo.increment_failed_login(user.id)
            logger.warning("login_wrong_password", user_id=str(user.id), attempts=new_count)
            await self._user_repo.create_audit_log(
                action=AuditAction.FAILED_LOGIN,
                user_id=user.id,
                ip_address=ip_address,
                details={"reason": "wrong_password", "attempt": new_count},
            )

            # Apply lockout if threshold reached
            await self._maybe_lock(user.id, new_count)

            raise AuthenticationError("Credenciales incorrectas")

        # --- Step 5: Rehash if needed (transparent upgrade) ---
        if self._hasher.needs_rehash(user.hashed_password):
            new_hash = self._hasher.hash(password)
            await self._user_repo.update_password(user.id, new_hash)
            logger.info("password_rehashed", user_id=str(user.id))

        # --- Step 6: Get permissions ---
        permissions = await self._user_repo.get_user_permissions(user.id)

        # --- Step 7: Issue tokens ---
        role_name = user.role.name if user.role else "CONSULTOR"

        access_token, access_jti, access_expires = self._jwt.create_access_token(
            user_id=str(user.id),
            role=role_name,
            permissions=permissions,
        )
        refresh_token, refresh_jti, refresh_expires = self._jwt.create_refresh_token(
            user_id=str(user.id),
        )

        # --- Step 8: Update login record ---
        await self._user_repo.update_last_login(user.id)

        # --- Step 9: Audit log ---
        await self._user_repo.create_audit_log(
            action=AuditAction.LOGIN,
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        logger.info("login_success", user_id=str(user.id), role=role_name)

        return LoginResult(
            access_token=access_token,
            refresh_token=refresh_token,
            access_jti=access_jti,
            refresh_jti=refresh_jti,
            access_expires_at=access_expires,
            refresh_expires_at=refresh_expires,
            user_id=str(user.id),
            user_email=user.email,
            user_full_name=user.full_name,
            role_name=role_name,
            permissions=permissions,
        )

    async def _maybe_lock(self, user_id: uuid.UUID, failed_count: int) -> None:
        """Apply progressive account lockout based on failure count."""
        lockout_minutes = None
        for threshold, minutes in reversed(LOCKOUT_SCHEDULE):
            if failed_count >= threshold:
                lockout_minutes = minutes
                break

        if lockout_minutes:
            locked_until = datetime.now(tz=timezone.utc) + timedelta(minutes=lockout_minutes)
            await self._user_repo.lock_account(user_id, locked_until)
            await self._user_repo.create_audit_log(
                action=AuditAction.ACCOUNT_LOCKED,
                user_id=user_id,
                details={"locked_minutes": lockout_minutes, "failed_count": failed_count},
            )
