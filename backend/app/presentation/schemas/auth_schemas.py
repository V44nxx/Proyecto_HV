"""
Pydantic schemas for authentication endpoints.

These are the HTTP-layer request/response models.
They are separate from domain entities and ORM models.
"""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


# ---- Requests ----

class LoginRequest(BaseModel):
    """POST /auth/login body."""

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.lower().strip()


class RefreshRequest(BaseModel):
    """POST /auth/refresh body (when not using cookie)."""

    refresh_token: str


class ChangePasswordRequest(BaseModel):
    """POST /auth/change-password body."""

    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=12, max_length=128)
    new_password_confirm: str = Field(min_length=12, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        errors = []
        if not any(c.isupper() for c in v):
            errors.append("debe contener al menos una mayúscula")
        if not any(c.islower() for c in v):
            errors.append("debe contener al menos una minúscula")
        if not any(c.isdigit() for c in v):
            errors.append("debe contener al menos un dígito")
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v):
            errors.append("debe contener al menos un carácter especial")
        if errors:
            raise ValueError("La contraseña " + ", ".join(errors))
        return v

    @field_validator("new_password_confirm")
    @classmethod
    def passwords_match(cls, v: str, info: object) -> str:
        data = getattr(info, "data", {})
        if "new_password" in data and v != data["new_password"]:
            raise ValueError("Las contraseñas no coinciden")
        return v


# ---- Responses ----

class TokenResponse(BaseModel):
    """Successful login/refresh response."""

    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    user: "UserBriefResponse"


class UserBriefResponse(BaseModel):
    """Minimal user info embedded in auth responses."""

    id: str
    email: str
    full_name: str
    role: str

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    """Generic success message."""

    message: str


# ---- User management schemas ----

class CreateUserRequest(BaseModel):
    """POST /users body."""

    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    full_name: str = Field(min_length=2, max_length=255)
    role_name: str = Field(description="Nombre del rol: ADMIN, DIRECTOR, GESTOR, CONSULTOR")

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.lower().strip()

    @field_validator("role_name")
    @classmethod
    def validate_role(cls, v: str) -> str:
        valid = {"ADMIN", "DIRECTOR", "GESTOR", "CONSULTOR"}
        if v.upper() not in valid:
            raise ValueError(f"Rol inválido. Opciones: {', '.join(sorted(valid))}")
        return v.upper()


class UpdateUserRequest(BaseModel):
    """PATCH /users/{id} body — all fields optional."""

    full_name: str | None = Field(default=None, min_length=2, max_length=255)
    role_name: str | None = Field(default=None)
    is_active: bool | None = None

    @field_validator("role_name")
    @classmethod
    def validate_role(cls, v: str | None) -> str | None:
        if v is None:
            return v
        valid = {"ADMIN", "DIRECTOR", "GESTOR", "CONSULTOR"}
        if v.upper() not in valid:
            raise ValueError(f"Rol inválido. Opciones: {', '.join(sorted(valid))}")
        return v.upper()


class UserResponse(BaseModel):
    """Full user info response."""

    id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    is_verified: bool
    last_login_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    """Paginated user list."""

    items: list[UserResponse]
    total: int
    skip: int
    limit: int


class RoleResponse(BaseModel):
    """Role info."""

    id: str
    name: str
    description: str | None

    model_config = {"from_attributes": True}
