"""
FastAPI dependencies for authentication and authorization.

These are the building blocks used in every protected route:

    get_current_user:
        Validates the JWT access token, checks revocation,
        and returns the authenticated user's payload.

    require_permission(resource, action):
        Factory that returns a dependency enforcing a specific permission.
        Used as:
            @router.get("/documents")
            async def list_docs(
                _=Depends(require_permission("documents", "read"))
            ):

    get_redis:
        Provides a Redis connection for token revocation checks.
"""

from dataclasses import dataclass
from typing import Annotated, Any

import structlog
from fastapi import Cookie, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.asyncio import Redis, from_url
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.infrastructure.database.session import get_db_session
from app.infrastructure.database.repositories.user_repository import UserRepository
from app.infrastructure.security.jwt_handler import JWTHandler, TokenError, TokenExpiredError
from app.infrastructure.security.token_revocation import TokenRevocationStore

logger = structlog.get_logger(__name__)
_settings = get_settings()

# ---- OAuth2 Bearer scheme (reads Authorization header) ----
_bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthenticatedUser:
    """
    Compact representation of the authenticated user extracted from JWT.
    Avoids a DB round-trip on every request — permissions are in the token.
    """
    user_id: str
    role: str
    permissions: list[str]
    jti: str


# ---- Redis connection pool (singleton per process) ----
_redis_pool: Redis | None = None  # type: ignore[type-arg]


class _InMemoryRedis:
    """In-memory fallback for token revocation when Redis is not available locally."""
    def __init__(self) -> None:
        self._store: dict[str, str] = {}
    async def setex(self, key: str, ttl: int, val: str) -> None:
        self._store[key] = val
    async def exists(self, key: str) -> int:
        return 1 if key in self._store else 0
    async def ping(self) -> bool:
        return True


async def get_redis() -> Any:
    """Provide a Redis client. Falls back to in-memory store if Redis is offline."""
    global _redis_pool
    if _redis_pool is None:
        try:
            client = await from_url(
                _settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            await client.ping()
            _redis_pool = client
        except Exception:
            logger.warning("redis_unavailable_using_in_memory_fallback")
            _redis_pool = _InMemoryRedis()
    return _redis_pool


# ---- get_current_user dependency ----

async def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)] = None,
    redis: Redis = Depends(get_redis),  # type: ignore[type-arg]
) -> AuthenticatedUser:
    """
    Validates the JWT from the Authorization: Bearer header.

    Raises 401 if:
    - No token provided
    - Token is expired
    - Token is invalid
    - Token has been revoked
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No autenticado o sesión expirada. Inicie sesión nuevamente.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not credentials:
        raise credentials_exception

    jwt_handler = JWTHandler()
    try:
        payload = jwt_handler.decode_access_token(credentials.credentials)
    except TokenExpiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Su sesión ha expirado. Inicie sesión nuevamente.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except TokenError:
        raise credentials_exception

    jti = payload.get("jti")
    user_id = payload.get("sub")
    role = payload.get("role", "")
    permissions = payload.get("permissions", [])

    if not jti or not user_id:
        raise credentials_exception

    # Check revocation (logout invalidation)
    revocation_store = TokenRevocationStore(redis)
    if await revocation_store.is_revoked(jti):
        logger.warning("revoked_token_used", jti=jti, user_id=user_id)
        raise credentials_exception

    # Bind user context to structured logs for this request
    import structlog
    structlog.contextvars.bind_contextvars(user_id=user_id, role=role)

    return AuthenticatedUser(
        user_id=user_id,
        role=role,
        permissions=permissions,
        jti=jti,
    )


# ---- require_permission factory ----

def require_permission(resource: str, action: str):  # type: ignore[return]
    """
    Returns a FastAPI dependency that enforces a specific permission.

    Usage:
        @router.post("/documents")
        async def upload(
            current_user: AuthenticatedUser = Depends(require_permission("documents", "write"))
        ):

    This is the SINGLE authoritative RBAC check point.
    Never check permissions in business logic — only here.
    """
    permission_key = f"{resource}:{action}"

    async def _check_permission(
        current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    ) -> AuthenticatedUser:
        if permission_key not in current_user.permissions:
            logger.warning(
                "permission_denied",
                user_id=current_user.user_id,
                required=permission_key,
                has=current_user.permissions,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"No tiene permiso para realizar esta acción: {resource}:{action}",
            )
        return current_user

    return Depends(_check_permission)


# ---- Typed annotated shortcuts (convenience aliases) ----

CurrentUser = Annotated[AuthenticatedUser, Depends(get_current_user)]
DbSession = Annotated[AsyncSession, Depends(get_db_session)]


def get_user_repo(db: DbSession) -> UserRepository:
    """FastAPI dependency that provides a UserRepository."""
    return UserRepository(db)
