"""
Use case: Change password

Verifies current password, validates new password strength,
hashes it, saves it, and invalidates all existing tokens.
"""

import uuid

import structlog

from app.config.constants import AuditAction
from app.infrastructure.database.repositories.user_repository import UserRepository
from app.infrastructure.security.password_hasher import PasswordHasher

logger = structlog.get_logger(__name__)


class ChangePasswordUseCase:
    def __init__(
        self,
        user_repo: UserRepository,
        hasher: PasswordHasher,
    ) -> None:
        self._user_repo = user_repo
        self._hasher = hasher

    async def execute(
        self,
        user_id: str,
        current_password: str,
        new_password: str,
        ip_address: str | None = None,
    ) -> None:
        from app.application.use_cases.auth.exceptions import InvalidPasswordError, UserNotFoundError

        uid = uuid.UUID(user_id)
        user = await self._user_repo.get_by_id(uid)
        if not user:
            raise UserNotFoundError("Usuario no encontrado")

        # Verify current password
        if not self._hasher.verify(user.hashed_password, current_password):
            logger.warning("change_password_wrong_current", user_id=user_id)
            raise InvalidPasswordError("La contraseña actual es incorrecta")

        # Ensure new password is different
        if self._hasher.verify(user.hashed_password, new_password):
            raise InvalidPasswordError("La nueva contraseña debe ser diferente a la actual")

        # Hash and save
        new_hash = self._hasher.hash(new_password)
        await self._user_repo.update_password(uid, new_hash)

        # Audit
        await self._user_repo.create_audit_log(
            action=AuditAction.PASSWORD_CHANGED,
            user_id=uid,
            ip_address=ip_address,
        )
        logger.info("password_changed", user_id=user_id)
