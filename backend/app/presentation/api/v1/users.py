"""
Users API router.

Endpoints:
    GET  /users           — list all users (ADMIN only)
    POST /users           — create user (ADMIN only)
    GET  /users/me        — get own profile (any authenticated)
    GET  /users/{id}      — get user by ID (ADMIN only)
    PATCH /users/{id}     — update user (ADMIN only)
    DELETE /users/{id}    — deactivate user (ADMIN only)
    GET  /users/roles     — list available roles (ADMIN only)
"""

import uuid

from fastapi import APIRouter, HTTPException, Query, status

from app.application.use_cases.auth.exceptions import (
    AuthorizationError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from app.application.use_cases.users.user_management import (
    CreateUserUseCase,
    DeactivateUserUseCase,
    ListUsersUseCase,
    UpdateUserUseCase,
    UserData,
)
from app.infrastructure.database.repositories.user_repository import UserRepository
from app.infrastructure.security.password_hasher import PasswordHasher
from app.presentation.dependencies.auth import CurrentUser, DbSession, require_permission
from app.presentation.schemas.auth_schemas import (
    CreateUserRequest,
    MessageResponse,
    RoleResponse,
    UpdateUserRequest,
    UserListResponse,
    UserResponse,
)

router = APIRouter(prefix="/users", tags=["Usuarios"])


def _to_response(data: UserData) -> UserResponse:
    return UserResponse(
        id=data.id,
        email=data.email,
        full_name=data.full_name,
        role=data.role,
        is_active=data.is_active,
        is_verified=data.is_verified,
        last_login_at=data.last_login_at,
        created_at=data.created_at,
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Ver mi perfil",
)
async def get_my_profile(
    current_user: CurrentUser,
    db: DbSession,
) -> UserResponse:
    """Returns the authenticated user's profile. Available to all authenticated users."""
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(uuid.UUID(current_user.user_id))
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    return UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role=user.role.name if user.role else "",
        is_active=user.is_active,
        is_verified=user.is_verified,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
    )


@router.get(
    "",
    response_model=UserListResponse,
    summary="Listar usuarios",
    dependencies=[require_permission("users", "manage")],
)
async def list_users(
    db: DbSession,
    current_user: CurrentUser,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    is_active: bool | None = Query(default=None),
) -> UserListResponse:
    user_repo = UserRepository(db)
    use_case = ListUsersUseCase(user_repo)
    users, total = await use_case.execute(skip=skip, limit=limit, is_active=is_active)
    return UserListResponse(
        items=[_to_response(u) for u in users],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear usuario",
    dependencies=[require_permission("users", "manage")],
)
async def create_user(
    body: CreateUserRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> UserResponse:
    user_repo = UserRepository(db)
    hasher = PasswordHasher()
    use_case = CreateUserUseCase(user_repo, hasher)
    try:
        data = await use_case.execute(
            email=body.email,
            password=body.password,
            full_name=body.full_name,
            role_name=body.role_name,
            created_by_id=current_user.user_id,
        )
    except UserAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    return _to_response(data)


@router.get(
    "/roles",
    response_model=list[RoleResponse],
    summary="Listar roles disponibles",
    dependencies=[require_permission("users", "manage")],
)
async def list_roles(db: DbSession) -> list[RoleResponse]:
    user_repo = UserRepository(db)
    roles = await user_repo.list_roles()
    return [
        RoleResponse(id=str(r.id), name=r.name, description=r.description)
        for r in roles
    ]


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Ver usuario por ID",
    dependencies=[require_permission("users", "manage")],
)
async def get_user(user_id: uuid.UUID, db: DbSession) -> UserResponse:
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    return UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role=user.role.name if user.role else "",
        is_active=user.is_active,
        is_verified=user.is_verified,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
    )


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    summary="Actualizar usuario",
    dependencies=[require_permission("users", "manage")],
)
async def update_user(
    user_id: uuid.UUID,
    body: UpdateUserRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> UserResponse:
    user_repo = UserRepository(db)
    use_case = UpdateUserUseCase(user_repo)
    try:
        data = await use_case.execute(
            target_user_id=str(user_id),
            full_name=body.full_name,
            role_name=body.role_name,
            is_active=body.is_active,
            modified_by_id=current_user.user_id,
        )
    except UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    return _to_response(data)


@router.delete(
    "/{user_id}",
    response_model=MessageResponse,
    summary="Desactivar usuario",
    dependencies=[require_permission("users", "manage")],
)
async def deactivate_user(
    user_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> MessageResponse:
    user_repo = UserRepository(db)
    use_case = DeactivateUserUseCase(user_repo)
    try:
        await use_case.execute(
            target_user_id=str(user_id),
            deleted_by_id=current_user.user_id,
        )
    except UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except AuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=exc.message)

    return MessageResponse(message="Usuario desactivado correctamente")
