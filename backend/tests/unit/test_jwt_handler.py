"""
Unit tests for JWTHandler.
"""

from datetime import datetime, timezone

import pytest

from app.infrastructure.security.jwt_handler import (
    JWTHandler,
    TokenError,
    TokenExpiredError,
    TokenType,
)


class TestJWTHandler:

    def setup_method(self) -> None:
        self.handler = JWTHandler()

    def test_create_access_token_returns_three_values(self) -> None:
        token, jti, expires = self.handler.create_access_token(
            user_id="user-123", role="GESTOR", permissions=["documents:read"]
        )
        assert isinstance(token, str)
        assert isinstance(jti, str)
        assert isinstance(expires, datetime)

    def test_access_token_is_decodable(self) -> None:
        token, jti, _ = self.handler.create_access_token(
            user_id="user-abc", role="ADMIN", permissions=["documents:read", "users:manage"]
        )
        payload = self.handler.decode_access_token(token)
        assert payload["sub"] == "user-abc"
        assert payload["role"] == "ADMIN"
        assert "documents:read" in payload["permissions"]
        assert payload["jti"] == jti
        assert payload["type"] == TokenType.ACCESS

    def test_refresh_token_is_decodable(self) -> None:
        token, jti, _ = self.handler.create_refresh_token(user_id="user-xyz")
        payload = self.handler.decode_refresh_token(token)
        assert payload["sub"] == "user-xyz"
        assert payload["type"] == TokenType.REFRESH
        assert payload["jti"] == jti

    def test_access_token_rejected_as_refresh(self) -> None:
        token, _, _ = self.handler.create_access_token(
            user_id="u", role="ADMIN", permissions=[]
        )
        with pytest.raises(TokenError):
            self.handler.decode_refresh_token(token)

    def test_refresh_token_rejected_as_access(self) -> None:
        token, _, _ = self.handler.create_refresh_token(user_id="u")
        with pytest.raises(TokenError):
            self.handler.decode_access_token(token)

    def test_tampered_token_raises_token_error(self) -> None:
        token, _, _ = self.handler.create_access_token(
            user_id="u", role="ADMIN", permissions=[]
        )
        tampered = token[:-10] + "TAMPERED!!"
        with pytest.raises(TokenError):
            self.handler.decode_access_token(tampered)

    def test_jti_is_unique_per_token(self) -> None:
        _, jti1, _ = self.handler.create_access_token("u", "ADMIN", [])
        _, jti2, _ = self.handler.create_access_token("u", "ADMIN", [])
        assert jti1 != jti2

    def test_expiry_is_in_the_future(self) -> None:
        _, _, expires = self.handler.create_access_token("u", "ADMIN", [])
        assert expires > datetime.now(tz=timezone.utc)
