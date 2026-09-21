"""
Storage provider interface (Port).

Defines the contract for storing and retrieving raw document files.
The application domain never depends on a specific storage backend.
"""

from abc import ABC, abstractmethod


class StorageError(Exception):
    """Base exception for storage errors."""
    pass


class StorageFileNotFoundError(StorageError):
    """Raised when a requested file does not exist in storage."""
    pass


class StoragePathTraversalError(StorageError):
    """Raised when an attempt to escape the storage root is detected."""
    pass


class StorageProvider(ABC):
    """
    Abstract interface for document file storage.
    Implementations may use local disk, MinIO, AWS S3, etc.
    """

    @abstractmethod
    async def save(self, file_bytes: bytes, key: str) -> str:
        """
        Store raw bytes under the given storage key.

        Args:
            file_bytes: Raw binary content to store.
            key: Canonical storage key (e.g. 'documents/2026/09/uuid.pdf').

        Returns:
            The stored key/path.
        """
        ...

    @abstractmethod
    async def get(self, key: str) -> bytes:
        """
        Retrieve raw bytes for the given storage key.

        Args:
            key: Storage key.

        Returns:
            Raw file bytes.

        Raises:
            StorageFileNotFoundError: If file does not exist.
        """
        ...

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """
        Delete the file at the given storage key.

        Args:
            key: Storage key.

        Returns:
            True if file was deleted, False if it was not found.
        """
        ...

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """
        Check if a file exists under the given storage key.

        Args:
            key: Storage key.

        Returns:
            True if file exists, False otherwise.
        """
        ...

    @abstractmethod
    async def get_url(self, key: str) -> str:
        """
        Get an accessible URL or reference path for the given key.

        Args:
            key: Storage key.

        Returns:
            URL or relative path.
        """
        ...
