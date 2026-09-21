"""
Password hashing using Argon2id.

Argon2id is the OWASP-recommended password hashing algorithm (2024).
It provides resistance against GPU/ASIC attacks and side-channel attacks.

NEVER use MD5, SHA-1, SHA-256, or bcrypt-128 for password storage.
"""

from argon2 import PasswordHasher as Argon2PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.config.settings import get_settings

_settings = get_settings()


class PasswordHasher:
    """
    Wrapper around argon2-cffi providing password hashing and verification.
    Parameters are loaded from application settings (not hardcoded).
    """

    def __init__(self) -> None:
        self._hasher = Argon2PasswordHasher(
            time_cost=_settings.argon2_time_cost,
            memory_cost=_settings.argon2_memory_cost,
            parallelism=_settings.argon2_parallelism,
        )

    def hash(self, password: str) -> str:
        """
        Hash a plaintext password using Argon2id.
        Returns a string that includes the algorithm, parameters, salt, and hash.
        """
        if not password:
            raise ValueError("Password cannot be empty")
        if len(password) > 1024:
            raise ValueError("Password too long")
        return self._hasher.hash(password)

    def verify(self, hashed_password: str, plaintext_password: str) -> bool:
        """
        Verify a plaintext password against its hash.
        Returns True if matching, False otherwise.
        Does NOT raise exceptions for mismatches (only for invalid hash format).
        """
        try:
            return self._hasher.verify(hashed_password, plaintext_password)
        except VerifyMismatchError:
            return False
        except (VerificationError, InvalidHashError):
            return False

    def needs_rehash(self, hashed_password: str) -> bool:
        """
        Check if a hash needs to be upgraded to current parameters.
        Call this after a successful verification to upgrade if needed.
        """
        return self._hasher.check_needs_rehash(hashed_password)
