"""Domain exceptions for authentication use cases."""


class AuthenticationError(Exception):
    """Raised when authentication fails for any reason."""

    def __init__(self, message: str = "Credenciales incorrectas") -> None:
        super().__init__(message)
        self.message = message


class AuthorizationError(Exception):
    """Raised when an authenticated user lacks required permissions."""

    def __init__(self, message: str = "No tiene permisos para realizar esta acción") -> None:
        super().__init__(message)
        self.message = message


class AccountLockedError(AuthenticationError):
    """Raised when a user account is locked."""
    pass


class TokenRevokedException(AuthenticationError):
    """Raised when a revoked token is presented."""
    pass


class UserNotFoundError(Exception):
    """Raised when a requested user does not exist."""
    pass


class UserAlreadyExistsError(Exception):
    """Raised when trying to create a user with a duplicate email."""
    pass


class InvalidPasswordError(Exception):
    """Raised when current password verification fails during change-password."""
    pass
