"""
JWT handler: access tokens and refresh tokens.

Strategy:
- Access Token: short-lived (15 min), stored in memory (JS variable)
- Refresh Token: long-lived (7 days), stored in HttpOnly Secure cookie
- Both are signed RS256 or HS256 (configurable)
- JTI (JWT ID) stored in Redis for revocation support

Token structure:
    {
        "sub": "user_uuid",
        "role": "GESTOR",
        "permissions": ["documents:read", "documents:write"],
        "type": "access" | "refresh",
        "jti": "unique_token_id",
        "iat": timestamp,
        "exp": timestamp
    }
"""

import uuid
from datetime import datetime, timedelta, timezone
from enum import StrEnum

import structlog
from jose import JWTError, jwt
from jose.exceptions import ExpiredSignatureError

from app.config.settings import get_settings

logger = structlog.get_logger(__name__)
_settings = get_settings()

ALGORITHM = "HS256"


class TokenType(StrEnum):
    ACCESS = "access"
    REFRESH = "refresh"


class TokenError(Exception):
    """Raised when a JWT cannot be validated."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class TokenExpiredError(TokenError):
    """Raised specifically when a token has expired (allows refresh flow)."""
    pass


class JWTHandler:
    """
    Handles creation and validation of JWT access and refresh tokens.
    Does NOT interact with the database — pure token logic.
    """

    def __init__(self) -> None:
        self._secret = _settings.secret_key
        self._access_expire_minutes = _settings.access_token_expire_minutes
        self._refresh_expire_days = _settings.refresh_token_expire_days

    def create_access_token(
        self,
        user_id: str,
        role: str,
        permissions: list[str],
    ) -> tuple[str, str, datetime]:
        """
        Create a short-lived access token.

        Returns:
            (token_string, jti, expiry_datetime)
        """
        jti = str(uuid.uuid4())
        now = datetime.now(tz=timezone.utc)
        expires_at = now + timedelta(minutes=self._access_expire_minutes)

        payload = {
            "sub": user_id,
            "role": role,
            "permissions": permissions,
            "type": TokenType.ACCESS,
            "jti": jti,
            "iat": now,
            "exp": expires_at,
        }

        token = jwt.encode(payload, self._secret, algorithm=ALGORITHM)
        logger.debug("access_token_created", user_id=user_id, jti=jti)
        return token, jti, expires_at

    def create_refresh_token(
        self,
        user_id: str,
    ) -> tuple[str, str, datetime]:
        """
        Create a long-lived refresh token.

        Returns:
            (token_string, jti, expiry_datetime)
        """
        jti = str(uuid.uuid4())
        now = datetime.now(tz=timezone.utc)
        expires_at = now + timedelta(days=self._refresh_expire_days)

        payload = {
            "sub": user_id,
            "type": TokenType.REFRESH,
            "jti": jti,
            "iat": now,
            "exp": expires_at,
        }

        token = jwt.encode(payload, self._secret, algorithm=ALGORITHM)
        logger.debug("refresh_token_created", user_id=user_id, jti=jti)
        return token, jti, expires_at

    def decode_access_token(self, token: str) -> dict:
        """
        Decode and validate an access token.

        Raises:
            TokenExpiredError: if the token has expired
            TokenError: if the token is invalid for any other reason
        """
        return self._decode(token, expected_type=TokenType.ACCESS)

    def decode_refresh_token(self, token: str) -> dict:
        """
        Decode and validate a refresh token.

        Raises:
            TokenExpiredError: if the token has expired
            TokenError: if the token is invalid for any other reason
        """
        return self._decode(token, expected_type=TokenType.REFRESH)

    def _decode(self, token: str, expected_type: TokenType) -> dict:
        try:
            payload = jwt.decode(token, self._secret, algorithms=[ALGORITHM])
        except ExpiredSignatureError:
            raise TokenExpiredError("Token ha expirado")
        except JWTError as exc:
            raise TokenError(f"Token inválido: {exc}") from exc

        token_type = payload.get("type")
        if token_type != expected_type:
            raise TokenError(
                f"Tipo de token incorrecto: esperado '{expected_type}', "
                f"recibido '{token_type}'"
            )

        return payload
