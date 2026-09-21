"""Use cases for user management (create, list, update, deactivate)."""

import uuid
from dataclasses import dataclass
from datetime import datetime

import structlog

from app.config.constants import AuditAction
from app.infrastructure.database.models.user_models import User
from app.infrastructure.database.repositories.user_repository import UserRepository
from app.infrastructure.security.password_hasher import PasswordHasher

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class UserData:
    """Read model for user information."""
    id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    is_verified: bool
    last_login_at: datetime | None
    created_at: datetime

    @classmethod
    def from_orm(cls, user: User) -> "UserData":
        return cls(
            id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            role=user.role.name if user.role else "UNKNOWN",
            is_active=user.is_active,
            is_verified=user.is_verified,
            last_login_at=user.last_login_at,
            created_at=user.created_at,
        )


class CreateUserUseCase:
    """Creates a new system user. Only ADMIN can do this."""

    def __init__(
        self,
        user_repo: UserRepository,
        hasher: PasswordHasher,
    ) -> None:
        self._user_repo = user_repo
        self._hasher = hasher

    async def execute(
        self,
        email: str,
        password: str,
        full_name: str,
        role_name: str,
        created_by_id: str,
    ) -> UserData:
        from app.application.use_cases.auth.exceptions import (
            UserAlreadyExistsError,
            UserNotFoundError,
        )

        # Check duplicate
        existing = await self._user_repo.get_by_email(email)
        if existing:
            raise UserAlreadyExistsError(f"Ya existe un usuario con el email: {email}")

        # Resolve role
        role = await self._user_repo.get_role_by_name(role_name)
        if not role:
            raise UserNotFoundError(f"Rol no encontrado: {role_name}")

        # Hash password
        hashed = self._hasher.hash(password)

        # Create user
        user = await self._user_repo.create(
            email=email,
            hashed_password=hashed,
            full_name=full_name,
            role_id=role.id,
            is_verified=True,  # Created by admin = pre-verified
        )

        # Audit
        await self._user_repo.create_audit_log(
            action=AuditAction.CREATE_USER,
            user_id=uuid.UUID(created_by_id),
            resource="users",
            resource_id=user.id,
            details={"email": email, "role": role_name},
        )
        logger.info("user_created_by_admin", new_user_id=str(user.id), by=created_by_id)

        # Reload with role relationship
        created = await self._user_repo.get_by_id(user.id)
        return UserData.from_orm(created)  # type: ignore[arg-type]


class ListUsersUseCase:
    def __init__(self, user_repo: UserRepository) -> None:
        self._user_repo = user_repo

    async def execute(
        self,
        skip: int = 0,
        limit: int = 50,
        is_active: bool | None = None,
    ) -> tuple[list[UserData], int]:
        users = await self._user_repo.list_users(skip=skip, limit=limit, is_active=is_active)
        total = await self._user_repo.count_users(is_active=is_active)
        return [UserData.from_orm(u) for u in users], total


class UpdateUserUseCase:
    def __init__(self, user_repo: UserRepository) -> None:
        self._user_repo = user_repo

    async def execute(
        self,
        target_user_id: str,
        full_name: str | None,
        role_name: str | None,
        is_active: bool | None,
        modified_by_id: str,
    ) -> UserData:
        from app.application.use_cases.auth.exceptions import UserNotFoundError

        uid = uuid.UUID(target_user_id)
        user = await self._user_repo.get_by_id(uid)
        if not user:
            raise UserNotFoundError("Usuario no encontrado")

        changes: dict = {}

        if role_name is not None:
            role = await self._user_repo.get_role_by_name(role_name)
            if not role:
                raise UserNotFoundError(f"Rol no encontrado: {role_name}")
            await self._user_repo.update_role(uid, role.id)
            changes["role"] = role_name

        if is_active is not None:
            await self._user_repo.set_active(uid, is_active)
            changes["is_active"] = is_active

        # Reload user
        updated = await self._user_repo.get_by_id(uid)

        await self._user_repo.create_audit_log(
            action=AuditAction.MODIFY_USER,
            user_id=uuid.UUID(modified_by_id),
            resource="users",
            resource_id=uid,
            details=changes,
        )
        return UserData.from_orm(updated)  # type: ignore[arg-type]


class DeactivateUserUseCase:
    def __init__(self, user_repo: UserRepository) -> None:
        self._user_repo = user_repo

    async def execute(self, target_user_id: str, deleted_by_id: str) -> None:
        from app.application.use_cases.auth.exceptions import UserNotFoundError

        uid = uuid.UUID(target_user_id)
        user = await self._user_repo.get_by_id(uid)
        if not user:
            raise UserNotFoundError("Usuario no encontrado")

        # Prevent self-deletion
        if target_user_id == deleted_by_id:
            from app.application.use_cases.auth.exceptions import AuthorizationError
            raise AuthorizationError("No puede desactivar su propia cuenta")

        await self._user_repo.soft_delete(uid)
        await self._user_repo.create_audit_log(
            action=AuditAction.DEACTIVATE_USER,
            user_id=uuid.UUID(deleted_by_id),
            resource="users",
            resource_id=uid,
        )
        logger.info("user_deactivated", target=target_user_id, by=deleted_by_id)
