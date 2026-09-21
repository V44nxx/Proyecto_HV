"""
Auth API router.

Endpoints:
    POST /auth/login           — authenticate with email/password
    POST /auth/logout          — revoke tokens
    POST /auth/refresh         — get new access token using refresh token
    POST /auth/change-password — change own password

Refresh token is stored in an HttpOnly Secure cookie.
Access token is returned in the response body.
"""

from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Cookie, HTTPException, Request, Response, status

from app.application.use_cases.auth.change_password import ChangePasswordUseCase
from app.application.use_cases.auth.exceptions import (
    AuthenticationError,
    InvalidPasswordError,
    UserNotFoundError,
)
from app.application.use_cases.auth.login import LoginUseCase
from app.application.use_cases.auth.logout import LogoutUseCase
from app.application.use_cases.auth.refresh_token import RefreshTokenUseCase
from app.infrastructure.database.repositories.user_repository import UserRepository
from app.infrastructure.security.jwt_handler import JWTHandler
from app.infrastructure.security.password_hasher import PasswordHasher
from app.infrastructure.security.token_revocation import TokenRevocationStore
from app.presentation.dependencies.auth import (
    CurrentUser,
    DbSession,
    get_redis,
)
from app.presentation.schemas.auth_schemas import (
    ChangePasswordRequest,
    LoginRequest,
    MessageResponse,
    TokenResponse,
    UserBriefResponse,
)

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["Autenticación"])

REFRESH_TOKEN_COOKIE = "refresh_token"
COOKIE_MAX_AGE_SECONDS = 7 * 24 * 60 * 60  # 7 days


def _build_token_response(login_result: object) -> TokenResponse:  # type: ignore[return]
    from app.application.use_cases.auth.login import LoginResult
    r: LoginResult = login_result  # type: ignore[assignment]
    return TokenResponse(
        access_token=r.access_token,
        expires_at=r.access_expires_at,
        user=UserBriefResponse(
            id=r.user_id,
            email=r.user_email,
            full_name=r.user_full_name,
            role=r.role_name,
        ),
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Iniciar sesión",
    description="Autenticación con correo y contraseña. Retorna un access token y establece un refresh token en cookie HttpOnly.",
)
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    db: DbSession,
    redis=__import__("fastapi").Depends(get_redis),
) -> TokenResponse:
    user_repo = UserRepository(db)
    hasher = PasswordHasher()
    jwt_handler = JWTHandler()

    use_case = LoginUseCase(user_repo, hasher, jwt_handler)

    ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    try:
        result = await use_case.execute(
            email=body.email,
            password=body.password,
            ip_address=ip,
            user_agent=user_agent,
        )
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=exc.message,
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Set refresh token in HttpOnly Secure cookie
    response.set_cookie(
        key=REFRESH_TOKEN_COOKIE,
        value=result.refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=COOKIE_MAX_AGE_SECONDS,
        path="/api/v1/auth",
    )

    return _build_token_response(result)


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Cerrar sesión",
)
async def logout(
    request: Request,
    response: Response,
    current_user: CurrentUser,
    db: DbSession,
    redis=__import__("fastapi").Depends(get_redis),
    refresh_token: str | None = Cookie(default=None, alias=REFRESH_TOKEN_COOKIE),
) -> MessageResponse:
    revocation_store = TokenRevocationStore(redis)
    user_repo = UserRepository(db)

    # Determine access token expiry from settings
    from app.config.settings import get_settings
    settings = get_settings()
    from datetime import timedelta
    access_expires = datetime.now(tz=timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )

    use_case = LogoutUseCase(user_repo, revocation_store)

    refresh_jti = None
    refresh_expires = None
    if refresh_token:
        jwt_handler = JWTHandler()
        try:
            payload = jwt_handler.decode_refresh_token(refresh_token)
            refresh_jti = payload.get("jti")
            exp = payload.get("exp", 0)
            refresh_expires = datetime.fromtimestamp(exp, tz=timezone.utc)
        except Exception:
            pass  # Expired/invalid refresh token — still logout access token

    ip = request.client.host if request.client else None
    await use_case.execute(
        user_id=current_user.user_id,
        access_jti=current_user.jti,
        access_expires_at=access_expires,
        refresh_jti=refresh_jti,
        refresh_expires_at=refresh_expires,
        ip_address=ip,
    )

    # Clear cookie
    response.delete_cookie(key=REFRESH_TOKEN_COOKIE, path="/api/v1/auth")

    return MessageResponse(message="Sesión cerrada correctamente")


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Renovar token de acceso",
)
async def refresh_token(
    response: Response,
    db: DbSession,
    redis=__import__("fastapi").Depends(get_redis),
    refresh_token_cookie: str | None = Cookie(default=None, alias=REFRESH_TOKEN_COOKIE),
) -> TokenResponse:
    if not refresh_token_cookie:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token no encontrado. Inicie sesión nuevamente.",
        )

    jwt_handler = JWTHandler()
    revocation_store = TokenRevocationStore(redis)
    user_repo = UserRepository(db)

    use_case = RefreshTokenUseCase(user_repo, jwt_handler, revocation_store, rotate_refresh=True)

    try:
        result = await use_case.execute(refresh_token_cookie)
    except AuthenticationError as exc:
        response.delete_cookie(key=REFRESH_TOKEN_COOKIE, path="/api/v1/auth")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=exc.message)

    # Rotate cookie if new refresh token was issued
    if result.new_refresh_token and result.new_refresh_expires_at:
        response.set_cookie(
            key=REFRESH_TOKEN_COOKIE,
            value=result.new_refresh_token,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=COOKIE_MAX_AGE_SECONDS,
            path="/api/v1/auth",
        )

    # Decode the new access token to get user info for the response
    import uuid as _uuid
    jwt_handler2 = JWTHandler()
    try:
        new_payload = jwt_handler2.decode_access_token(result.access_token)
        uid_str = new_payload.get("sub", "")
        role_str = new_payload.get("role", "")
    except Exception:
        uid_str, role_str = "", ""

    user = await user_repo.get_by_id(_uuid.UUID(uid_str)) if uid_str else None

    return TokenResponse(
        access_token=result.access_token,
        expires_at=result.access_expires_at,
        user=UserBriefResponse(
            id=uid_str,
            email=user.email if user else "",
            full_name=user.full_name if user else "",
            role=role_str,
        ),
    )


@router.post(
    "/change-password",
    response_model=MessageResponse,
    summary="Cambiar contraseña",
)
async def change_password(
    body: ChangePasswordRequest,
    request: Request,
    current_user: CurrentUser,
    db: DbSession,
) -> MessageResponse:
    hasher = PasswordHasher()
    user_repo = UserRepository(db)
    use_case = ChangePasswordUseCase(user_repo, hasher)

    ip = request.client.host if request.client else None

    try:
        await use_case.execute(
            user_id=current_user.user_id,
            current_password=body.current_password,
            new_password=body.new_password,
            ip_address=ip,
        )
    except (UserNotFoundError, InvalidPasswordError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    return MessageResponse(message="Contraseña actualizada correctamente")
