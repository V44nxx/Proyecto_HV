"""
Database seed script.

Creates initial roles, permissions, and the first ADMIN user.
Run this ONCE after the first migration:

    python -m scripts.seed_db

This script is idempotent — safe to run multiple times.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.constants import ROLE_PERMISSIONS, UserRole
from app.infrastructure.database.models import Permission, Role, RolePermission, User
from app.infrastructure.database.session import AsyncSessionFactory
from app.infrastructure.logging.structured_logger import configure_logging

logger = structlog.get_logger(__name__)


async def seed_roles_and_permissions(db: AsyncSession) -> dict[str, Role]:
    """Create system roles if they don't exist."""
    roles_config = [
        {"name": UserRole.ADMIN, "description": "Administrador con acceso total al sistema"},
        {"name": UserRole.DIRECTOR, "description": "Director con acceso a dashboards, búsqueda y reportes"},
        {"name": UserRole.GESTOR, "description": "Gestor de hojas de vida: sube, procesa y revisa documentos"},
        {"name": UserRole.CONSULTOR, "description": "Consultor: búsqueda y visualización autorizada"},
    ]

    roles: dict[str, Role] = {}
    for role_data in roles_config:
        result = await db.execute(select(Role).where(Role.name == role_data["name"]))
        role = result.scalar_one_or_none()
        if not role:
            role = Role(**role_data)
            db.add(role)
            await db.flush()
            logger.info("role_created", role=role_data["name"])
        else:
            logger.info("role_exists", role=role_data["name"])
        roles[role_data["name"]] = role

    return roles


async def seed_permissions(db: AsyncSession) -> dict[str, Permission]:
    """Create all permissions."""
    from app.config.constants import PERMISSIONS

    permissions: dict[str, Permission] = {}
    for resource, actions in PERMISSIONS.items():
        for action in actions:
            perm_key = f"{resource}:{action}"
            result = await db.execute(
                select(Permission).where(
                    Permission.resource == resource,
                    Permission.action == action,
                )
            )
            perm = result.scalar_one_or_none()
            if not perm:
                perm = Permission(resource=resource, action=action)
                db.add(perm)
                await db.flush()
                logger.info("permission_created", permission=perm_key)
            permissions[perm_key] = perm

    return permissions


async def seed_role_permissions(
    db: AsyncSession,
    roles: dict[str, Role],
    permissions: dict[str, Permission],
) -> None:
    """Assign permissions to roles."""
    for role_name, perm_keys in ROLE_PERMISSIONS.items():
        role = roles.get(role_name)
        if not role:
            continue
        for perm_key in perm_keys:
            perm = permissions.get(perm_key)
            if not perm:
                logger.warning("permission_not_found", key=perm_key)
                continue
            result = await db.execute(
                select(RolePermission).where(
                    RolePermission.role_id == role.id,
                    RolePermission.permission_id == perm.id,
                )
            )
            if not result.scalar_one_or_none():
                db.add(RolePermission(role_id=role.id, permission_id=perm.id))
                logger.info("role_permission_assigned", role=role_name, permission=perm_key)


async def seed_initial_admin(db: AsyncSession, roles: dict[str, Role]) -> None:
    """
    Create the initial admin user.
    Reads credentials from environment variables ADMIN_EMAIL and ADMIN_PASSWORD.
    """
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@proyecto-hv.local")
    admin_password = os.environ.get("ADMIN_PASSWORD")

    if not admin_password:
        logger.warning(
            "admin_password_not_set",
            message="Set ADMIN_PASSWORD env var to create initial admin user",
        )
        return

    result = await db.execute(select(User).where(User.email == admin_email))
    if result.scalar_one_or_none():
        logger.info("admin_user_exists", email=admin_email)
        return

    # Hash password (Argon2id)
    from app.infrastructure.security.password_hasher import PasswordHasher
    hasher = PasswordHasher()

    admin_role = roles.get(UserRole.ADMIN)
    if not admin_role:
        logger.error("admin_role_not_found")
        return

    admin = User(
        email=admin_email,
        hashed_password=hasher.hash(admin_password),
        full_name="Administrador del Sistema",
        role_id=admin_role.id,
        is_active=True,
        is_verified=True,
    )
    db.add(admin)
    logger.info("admin_user_created", email=admin_email)


async def main() -> None:
    configure_logging("INFO")
    logger.info("seed_start")

    async with AsyncSessionFactory() as db:
        try:
            roles = await seed_roles_and_permissions(db)
            permissions = await seed_permissions(db)
            await seed_role_permissions(db, roles, permissions)
            await seed_initial_admin(db, roles)
            await db.commit()
            logger.info("seed_completed")
        except Exception as exc:
            await db.rollback()
            logger.error("seed_failed", error=str(exc))
            raise


if __name__ == "__main__":
    asyncio.run(main())
