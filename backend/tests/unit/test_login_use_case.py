"""
Unit tests for Login use case.

Tests the business logic in isolation using mocks —
no database, no HTTP, no Redis.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.application.use_cases.auth.exceptions import AuthenticationError
from app.application.use_cases.auth.login import LOCKOUT_SCHEDULE, LoginUseCase
from app.infrastructure.security.jwt_handler import JWTHandler
from app.infrastructure.security.password_hasher import PasswordHasher


def _make_mock_user(
    *,
    is_active: bool = True,
    locked_until: datetime | None = None,
    failed_login_count: int = 0,
    role_name: str = "GESTOR",
) -> MagicMock:
    """Build a mock User ORM object."""
    user = MagicMock()
    user.id = MagicMock()
    user.email = "test@example.com"
    user.full_name = "Test User"
    user.is_active = is_active
    user.locked_until = locked_until
    user.failed_login_count = failed_login_count
    user.hashed_password = PasswordHasher().hash("Correct_Password_123!")
    user.role = MagicMock()
    user.role.name = role_name
    return user


def _make_use_case(mock_user: MagicMock | None, permissions: list[str] | None = None):
    """Build LoginUseCase with mocked dependencies."""
    user_repo = AsyncMock()
    user_repo.get_by_email.return_value = mock_user
    user_repo.get_user_permissions.return_value = permissions or ["documents:read"]
    user_repo.update_last_login.return_value = None
    user_repo.increment_failed_login.return_value = 1
    user_repo.lock_account.return_value = None
    user_repo.create_audit_log.return_value = None

    hasher = PasswordHasher()
    jwt_handler = JWTHandler()

    return LoginUseCase(user_repo, hasher, jwt_handler), user_repo


class TestLoginUseCase:

    @pytest.mark.asyncio
    async def test_successful_login_returns_tokens(self) -> None:
        user = _make_mock_user()
        use_case, repo = _make_use_case(user)

        result = await use_case.execute("test@example.com", "Correct_Password_123!")

        assert result.access_token
        assert result.refresh_token
        assert result.user_id
        assert result.role_name == "GESTOR"
        assert "documents:read" in result.permissions

    @pytest.mark.asyncio
    async def test_login_nonexistent_user_raises_auth_error(self) -> None:
        use_case, _ = _make_use_case(None)

        with pytest.raises(AuthenticationError) as exc_info:
            await use_case.execute("nobody@example.com", "password")

        # Must not reveal whether email exists
        assert "incorrectas" in exc_info.value.message.lower()

    @pytest.mark.asyncio
    async def test_login_wrong_password_raises_auth_error(self) -> None:
        user = _make_mock_user()
        use_case, repo = _make_use_case(user)

        with pytest.raises(AuthenticationError):
            await use_case.execute("test@example.com", "WRONG_password!")

        repo.increment_failed_login.assert_called_once()

    @pytest.mark.asyncio
    async def test_login_inactive_user_raises_auth_error(self) -> None:
        user = _make_mock_user(is_active=False)
        use_case, _ = _make_use_case(user)

        with pytest.raises(AuthenticationError) as exc_info:
            await use_case.execute("test@example.com", "Correct_Password_123!")

        assert "desactivada" in exc_info.value.message.lower()

    @pytest.mark.asyncio
    async def test_login_locked_account_raises_auth_error(self) -> None:
        future = datetime.now(tz=timezone.utc) + timedelta(minutes=10)
        user = _make_mock_user(locked_until=future)
        use_case, _ = _make_use_case(user)

        with pytest.raises(AuthenticationError) as exc_info:
            await use_case.execute("test@example.com", "Correct_Password_123!")

        assert "bloqueada" in exc_info.value.message.lower()

    @pytest.mark.asyncio
    async def test_login_expired_lock_is_ignored(self) -> None:
        """An expired lockout should not prevent login."""
        past = datetime.now(tz=timezone.utc) - timedelta(minutes=1)
        user = _make_mock_user(locked_until=past)
        use_case, _ = _make_use_case(user)

        result = await use_case.execute("test@example.com", "Correct_Password_123!")
        assert result.access_token

    @pytest.mark.asyncio
    async def test_login_audit_log_written_on_success(self) -> None:
        user = _make_mock_user()
        use_case, repo = _make_use_case(user)

        await use_case.execute("test@example.com", "Correct_Password_123!")

        repo.create_audit_log.assert_called()
        call_kwargs = repo.create_audit_log.call_args_list[-1].kwargs
        assert call_kwargs.get("action") == "LOGIN"

    @pytest.mark.asyncio
    async def test_login_audit_log_written_on_failure(self) -> None:
        user = _make_mock_user()
        use_case, repo = _make_use_case(user)

        with pytest.raises(AuthenticationError):
            await use_case.execute("test@example.com", "WRONG!")

        repo.create_audit_log.assert_called()
        call_kwargs = repo.create_audit_log.call_args_list[-1].kwargs
        assert "FAILED" in call_kwargs.get("action", "")

    @pytest.mark.asyncio
    async def test_lockout_applied_after_threshold(self) -> None:
        """Account should be locked after 5 failures."""
        user = _make_mock_user()
        use_case, repo = _make_use_case(user)
        repo.increment_failed_login.return_value = 5  # Simulate 5th failure

        with pytest.raises(AuthenticationError):
            await use_case.execute("test@example.com", "WRONG!")

        repo.lock_account.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_lockout_below_threshold(self) -> None:
        """Account should NOT be locked after < 5 failures."""
        user = _make_mock_user()
        use_case, repo = _make_use_case(user)
        repo.increment_failed_login.return_value = 3  # Below threshold

        with pytest.raises(AuthenticationError):
            await use_case.execute("test@example.com", "WRONG!")

        repo.lock_account.assert_not_called()
