"""
FastAPI dependencies for document management.
"""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.interfaces.storage_provider import StorageProvider
from app.infrastructure.database.repositories.document_repository import DocumentRepository
from app.infrastructure.database.repositories.user_repository import UserRepository
from app.infrastructure.database.session import get_db_session
from app.infrastructure.storage.storage_factory import get_storage_provider

DbSession = Annotated[AsyncSession, Depends(get_db_session)]


def get_document_repo(db: DbSession) -> DocumentRepository:
    """Provides a DocumentRepository bound to current DB session."""
    return DocumentRepository(db)


def get_user_repo(db: DbSession) -> UserRepository:
    """Provides a UserRepository bound to current DB session."""
    return UserRepository(db)


def get_storage() -> StorageProvider:
    """Provides the active StorageProvider instance."""
    return get_storage_provider()


DocumentRepo = Annotated[DocumentRepository, Depends(get_document_repo)]
UserRepo = Annotated[UserRepository, Depends(get_user_repo)]
Storage = Annotated[StorageProvider, Depends(get_storage)]
