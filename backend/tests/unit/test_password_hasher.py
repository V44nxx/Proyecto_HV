"""
Tests for PasswordHasher.

Verifies that:
- Hashing produces different outputs for the same input (salt randomness)
- Verification works correctly
- Wrong passwords are rejected
- Empty/oversized passwords raise errors
- needs_rehash works correctly
"""

import pytest

from app.infrastructure.security.password_hasher import PasswordHasher


class TestPasswordHasher:
    def setup_method(self) -> None:
        self.hasher = PasswordHasher()

    def test_hash_produces_non_empty_string(self) -> None:
        result = self.hasher.hash("secure_password_123")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_hash_includes_argon2_identifier(self) -> None:
        result = self.hasher.hash("test_password")
        assert "$argon2id$" in result

    def test_same_password_produces_different_hashes(self) -> None:
        """Salt randomness: identical passwords must produce different hashes."""
        password = "same_password"
        hash1 = self.hasher.hash(password)
        hash2 = self.hasher.hash(password)
        assert hash1 != hash2

    def test_verify_correct_password_returns_true(self) -> None:
        password = "correct_password"
        hashed = self.hasher.hash(password)
        assert self.hasher.verify(hashed, password) is True

    def test_verify_wrong_password_returns_false(self) -> None:
        hashed = self.hasher.hash("correct_password")
        assert self.hasher.verify(hashed, "wrong_password") is False

    def test_verify_empty_password_returns_false(self) -> None:
        hashed = self.hasher.hash("real_password")
        assert self.hasher.verify(hashed, "") is False

    def test_hash_empty_password_raises_error(self) -> None:
        with pytest.raises(ValueError, match="cannot be empty"):
            self.hasher.hash("")

    def test_hash_oversized_password_raises_error(self) -> None:
        with pytest.raises(ValueError, match="too long"):
            self.hasher.hash("x" * 1025)

    def test_verify_invalid_hash_returns_false(self) -> None:
        assert self.hasher.verify("not_a_valid_hash", "password") is False

    def test_needs_rehash_returns_bool(self) -> None:
        hashed = self.hasher.hash("password")
        result = self.hasher.needs_rehash(hashed)
        assert isinstance(result, bool)
        # Fresh hash with current settings should not need rehash
        assert result is False
