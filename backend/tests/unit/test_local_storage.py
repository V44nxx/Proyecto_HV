"""
Unit tests for LocalStorageProvider.
"""

import os
from pathlib import Path
import pytest
import pytest_asyncio

from app.application.interfaces.storage_provider import (
    StorageFileNotFoundError,
    StoragePathTraversalError,
)
from app.infrastructure.storage.local_storage import LocalStorageProvider


@pytest.fixture
def storage(tmp_path: Path) -> LocalStorageProvider:
    """Provide a LocalStorageProvider backed by pytest's tmp_path."""
    return LocalStorageProvider(base_path=tmp_path)


@pytest.mark.asyncio
async def test_save_and_get_file(storage: LocalStorageProvider) -> None:
    content = b"%PDF-1.4 sample content bytes"
    key = "documents/2026/09/sample.pdf"

    saved_key = await storage.save(file_bytes=content, key=key)
    assert saved_key == key

    exists = await storage.exists(key)
    assert exists is True

    retrieved = await storage.get(key)
    assert retrieved == content


@pytest.mark.asyncio
async def test_get_nonexistent_file_raises(storage: LocalStorageProvider) -> None:
    with pytest.raises(StorageFileNotFoundError):
        await storage.get("nonexistent/path/file.pdf")


@pytest.mark.asyncio
async def test_delete_file(storage: LocalStorageProvider) -> None:
    content = b"content to delete"
    key = "documents/to_delete.pdf"

    await storage.save(file_bytes=content, key=key)
    assert await storage.exists(key) is True

    deleted = await storage.delete(key)
    assert deleted is True
    assert await storage.exists(key) is False

    # Deleting again returns False (not found)
    deleted_again = await storage.delete(key)
    assert deleted_again is False


@pytest.mark.asyncio
async def test_path_traversal_protection(storage: LocalStorageProvider) -> None:
    malicious_keys = [
        "../../etc/passwd",
        "../secrets.txt",
        "documents/../../outside.txt",
        "/etc/shadow",
    ]

    for key in malicious_keys:
        with pytest.raises(StoragePathTraversalError):
            await storage.save(b"bad", key)

        with pytest.raises(StoragePathTraversalError):
            await storage.get(key)

        with pytest.raises(StoragePathTraversalError):
            await storage.exists(key)

        with pytest.raises(StoragePathTraversalError):
            await storage.delete(key)


@pytest.mark.asyncio
async def test_nested_directory_creation(storage: LocalStorageProvider) -> None:
    key = "a/b/c/d/e/deep.pdf"
    content = b"deeply nested"

    await storage.save(file_bytes=content, key=key)
    assert await storage.exists(key) is True
    assert await storage.get(key) == content
