"""
Local filesystem storage provider implementation.

Stores files under a configured base directory on the host filesystem.
Includes path traversal protection and automatic directory creation.
"""

import asyncio
from pathlib import Path

import aiofiles
import structlog

from app.application.interfaces.storage_provider import (
    StorageError,
    StorageFileNotFoundError,
    StoragePathTraversalError,
    StorageProvider,
)

logger = structlog.get_logger(__name__)


class LocalStorageProvider(StorageProvider):
    """
    Stores documents in the local filesystem.
    Suitable for development and single-server / VPS deployments.
    """

    def __init__(self, base_path: Path | str) -> None:
        self.base_path = Path(base_path).resolve()
        # Ensure root storage directory exists
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _resolve_safe_path(self, key: str) -> Path:
        """
        Safely resolve a storage key within the base storage path.
        Prevents directory traversal (e.g. '../../etc/passwd') and absolute paths.
        """
        raw_key = key.strip()
        if raw_key.startswith("/") or raw_key.startswith("\\") or Path(raw_key).is_absolute():
            logger.error("storage_absolute_path_attempt", key=key, base=str(self.base_path))
            raise StoragePathTraversalError(f"Ruta absoluta no permitida en clave de almacenamiento: {key}")

        normalized_key = raw_key.replace("\\", "/")
        candidate_path = (self.base_path / normalized_key).resolve()

        try:
            candidate_path.relative_to(self.base_path)
        except ValueError as exc:
            logger.error("storage_path_traversal_attempt", key=key, base=str(self.base_path))
            raise StoragePathTraversalError(f"Ruta de almacenamiento inválida: {key}") from exc

        return candidate_path

    async def save(self, file_bytes: bytes, key: str) -> str:
        """
        Save binary content to disk at the resolved path.
        Automatically creates parent directories.
        """
        path = self._resolve_safe_path(key)
        try:
            # Create parent directories if they don't exist
            await asyncio.to_thread(path.parent.mkdir, parents=True, exist_ok=True)

            async with aiofiles.open(path, "wb") as f:
                await f.write(file_bytes)

            logger.info("file_saved_locally", key=key, size=len(file_bytes), path=str(path))
            return key
        except Exception as exc:
            logger.error("file_save_failed", key=key, error=str(exc))
            raise StorageError(f"Error al guardar archivo en disco: {exc}") from exc

    async def get(self, key: str) -> bytes:
        """
        Read binary content from disk for the given storage key.
        """
        path = self._resolve_safe_path(key)
        if not path.is_file():
            logger.warning("file_not_found_in_storage", key=key, path=str(path))
            raise StorageFileNotFoundError(f"Archivo no encontrado en almacenamiento: {key}")

        try:
            async with aiofiles.open(path, "rb") as f:
                return await f.read()
        except Exception as exc:
            logger.error("file_read_failed", key=key, error=str(exc))
            raise StorageError(f"Error al leer archivo de almacenamiento: {exc}") from exc

    async def delete(self, key: str) -> bool:
        """
        Delete file from disk if it exists.
        """
        path = self._resolve_safe_path(key)
        if not path.is_file():
            return False

        try:
            await asyncio.to_thread(path.unlink, missing_ok=True)
            logger.info("file_deleted_locally", key=key)
            return True
        except Exception as exc:
            logger.error("file_delete_failed", key=key, error=str(exc))
            raise StorageError(f"Error al eliminar archivo: {exc}") from exc

    async def exists(self, key: str) -> bool:
        """
        Check if file exists on disk.
        """
        path = self._resolve_safe_path(key)
        return await asyncio.to_thread(path.is_file)

    async def get_url(self, key: str) -> str:
        """
        Return the logical path or access URL for the document.
        """
        return f"/api/v1/documents/files/{key}"
