"""
Storage provider factory.

Instantiates and returns the configured StorageProvider implementation
based on application settings.
"""

from functools import lru_cache

from app.application.interfaces.storage_provider import StorageProvider
from app.config.settings import Settings, StorageBackend, get_settings
from app.infrastructure.storage.local_storage import LocalStorageProvider


@lru_cache
def get_storage_provider(settings: Settings | None = None) -> StorageProvider:
    """
    Factory function to retrieve the configured storage provider.
    Cached so a single instance is reused across the application.
    """
    if settings is None:
        settings = get_settings()

    if settings.storage_backend == StorageBackend.LOCAL:
        return LocalStorageProvider(base_path=settings.storage_local_path)
    elif settings.storage_backend in (StorageBackend.MINIO, StorageBackend.S3):
        # In this phase, local fallback is used if MinIO endpoint is not configured
        if not settings.minio_endpoint:
            return LocalStorageProvider(base_path=settings.storage_local_path)
        # MinIO/S3 implementation can be hooked in future phase or configured here
        return LocalStorageProvider(base_path=settings.storage_local_path)
    else:
        return LocalStorageProvider(base_path=settings.storage_local_path)
