"""
User repository: database access for User, Role, Permission entities.

This is the concrete implementation of the user repository.
It lives in infrastructure/ because it knows about SQLAlchemy.
The domain should only depend on the abstract interface (added in later phases).
"""

import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.infrastructure.database.models.user_models import (
    AuditLog,
    Permission,
    Role,
    RolePermission,
    User,
)

logger = structlog.get_logger(__name__)


class UserRepository:
    """All database operations related to users, roles, and permissions."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ---- User queries ----

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        """Fetch a user by UUID, eager-loading their role."""
        result = await self._db.execute(
            select(User)
            .options(selectinload(User.role).selectinload(Role.role_permissions).selectinload(RolePermission.permission))
            .where(User.id == user_id, User.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        """Fetch a user by email (case-insensitive), eager-loading their role."""
        result = await self._db.execute(
            select(User)
            .options(selectinload(User.role).selectinload(Role.role_permissions).selectinload(RolePermission.permission))
            .where(User.email == email.lower().strip(), User.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def list_users(
        self,
        skip: int = 0,
        limit: int = 50,
        is_active: bool | None = None,
    ) -> list[User]:
        """List users with optional active filter, paginated."""
        query = (
            select(User)
            .options(selectinload(User.role))
            .where(User.deleted_at.is_(None))
            .order_by(User.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        if is_active is not None:
            query = query.where(User.is_active == is_active)

        result = await self._db.execute(query)
        return list(result.scalars().all())

    async def count_users(self, is_active: bool | None = None) -> int:
        """Count total users."""
        from sqlalchemy import func
        query = select(func.count()).select_from(User).where(User.deleted_at.is_(None))
        if is_active is not None:
            query = query.where(User.is_active == is_active)
        result = await self._db.execute(query)
        return result.scalar_one()

    async def create(
        self,
        email: str,
        hashed_password: str,
        full_name: str,
        role_id: uuid.UUID,
        is_verified: bool = False,
    ) -> User:
        """Create a new user."""
        user = User(
            email=email.lower().strip(),
            hashed_password=hashed_password,
            full_name=full_name,
            role_id=role_id,
            is_active=True,
            is_verified=is_verified,
        )
        self._db.add(user)
        await self._db.flush()  # Get the ID without committing
        logger.info("user_created", user_id=str(user.id), email=email)
        return user

    async def update_last_login(self, user_id: uuid.UUID) -> None:
        """Record successful login timestamp."""
        await self._db.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                last_login_at=datetime.now(tz=timezone.utc),
                failed_login_count=0,
                locked_until=None,
            )
        )

    async def increment_failed_login(self, user_id: uuid.UUID) -> int:
        """
        Increment failed login counter.
        Returns the new count so the caller can decide lockout.
        """
        result = await self._db.execute(
            select(User.failed_login_count).where(User.id == user_id)
        )
        current_count = result.scalar_one_or_none() or 0
        new_count = current_count + 1

        await self._db.execute(
            update(User)
            .where(User.id == user_id)
            .values(failed_login_count=new_count)
        )
        return new_count

    async def lock_account(self, user_id: uuid.UUID, locked_until: datetime) -> None:
        """Lock a user account until the given datetime."""
        await self._db.execute(
            update(User)
            .where(User.id == user_id)
            .values(locked_until=locked_until)
        )
        logger.warning("account_locked", user_id=str(user_id), until=locked_until.isoformat())

    async def update_password(self, user_id: uuid.UUID, hashed_password: str) -> None:
        """Update hashed password and record timestamp."""
        await self._db.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                hashed_password=hashed_password,
                password_changed_at=datetime.now(tz=timezone.utc),
            )
        )

    async def update_role(self, user_id: uuid.UUID, role_id: uuid.UUID) -> None:
        """Assign a new role to a user."""
        await self._db.execute(
            update(User)
            .where(User.id == user_id)
            .values(role_id=role_id)
        )

    async def set_active(self, user_id: uuid.UUID, is_active: bool) -> None:
        """Activate or deactivate a user account."""
        await self._db.execute(
            update(User).where(User.id == user_id).values(is_active=is_active)
        )

    async def soft_delete(self, user_id: uuid.UUID) -> None:
        """Soft-delete a user (sets deleted_at)."""
        await self._db.execute(
            update(User)
            .where(User.id == user_id)
            .values(deleted_at=datetime.now(tz=timezone.utc), is_active=False)
        )

    # ---- Role queries ----

    async def get_role_by_name(self, name: str) -> Role | None:
        result = await self._db.execute(
            select(Role).where(Role.name == name, Role.is_active.is_(True))
        )
        return result.scalar_one_or_none()

    async def list_roles(self) -> list[Role]:
        result = await self._db.execute(
            select(Role).where(Role.is_active.is_(True)).order_by(Role.name)
        )
        return list(result.scalars().all())

    async def get_user_permissions(self, user_id: uuid.UUID) -> list[str]:
        """
        Return all permissions for a user as a list of 'resource:action' strings.
        """
        result = await self._db.execute(
            select(Permission.resource, Permission.action)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(Role, Role.id == RolePermission.role_id)
            .join(User, User.role_id == Role.id)
            .where(User.id == user_id, User.deleted_at.is_(None))
        )
        rows = result.all()
        return [f"{row[0]}:{row[1]}" for row in rows]

    # ---- Audit log ----

    async def create_audit_log(
        self,
        action: str,
        user_id: uuid.UUID | None = None,
        resource: str | None = None,
        resource_id: uuid.UUID | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        details: dict | None = None,
    ) -> None:
        """
        Insert an immutable audit record.
        Never logs passwords or sensitive field values.
        """
        log = AuditLog(
            action=action,
            user_id=user_id,
            resource=resource,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details,
        )
        self._db.add(log)
        await self._db.flush()
