"""
FastAPI dependencies for document management.
"""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.interfaces.ocr_provider import OCRProvider
from app.application.interfaces.storage_provider import StorageProvider
from app.infrastructure.database.repositories.dashboard_repository import DashboardRepository
from app.infrastructure.database.repositories.document_repository import DocumentRepository
from app.infrastructure.database.repositories.person_repository import PersonRepository
from app.infrastructure.database.repositories.review_repository import ReviewRepository
from app.infrastructure.database.repositories.search_repository import SearchRepository
from app.infrastructure.database.repositories.user_repository import UserRepository
from app.infrastructure.database.session import get_db_session
from app.infrastructure.ocr.ocr_factory import get_ocr_provider
from app.infrastructure.storage.storage_factory import get_storage_provider

DbSession = Annotated[AsyncSession, Depends(get_db_session)]


def get_document_repo(db: DbSession) -> DocumentRepository:
    """Provides a DocumentRepository bound to current DB session."""
    return DocumentRepository(db)


def get_person_repo(db: DbSession) -> PersonRepository:
    """Provides a PersonRepository bound to current DB session."""
    return PersonRepository(db)


def get_review_repo(db: DbSession) -> ReviewRepository:
    """Provides a ReviewRepository bound to current DB session."""
    return ReviewRepository(db)


def get_search_repo(db: DbSession) -> SearchRepository:
    """Provides a SearchRepository bound to current DB session."""
    return SearchRepository(db)


def get_dashboard_repo(db: DbSession) -> DashboardRepository:
    """Provides a DashboardRepository bound to current DB session."""
    return DashboardRepository(db)


def get_user_repo(db: DbSession) -> UserRepository:
    """Provides a UserRepository bound to current DB session."""
    return UserRepository(db)


def get_storage() -> StorageProvider:
    """Provides the active StorageProvider instance."""
    return get_storage_provider()


def get_ocr() -> OCRProvider:
    """Provides the active OCRProvider instance."""
    return get_ocr_provider()


DocumentRepo = Annotated[DocumentRepository, Depends(get_document_repo)]
PersonRepo = Annotated[PersonRepository, Depends(get_person_repo)]
ReviewRepo = Annotated[ReviewRepository, Depends(get_review_repo)]
SearchRepo = Annotated[SearchRepository, Depends(get_search_repo)]
DashboardRepo = Annotated[DashboardRepository, Depends(get_dashboard_repo)]
UserRepo = Annotated[UserRepository, Depends(get_user_repo)]
Storage = Annotated[StorageProvider, Depends(get_storage)]
OCR = Annotated[OCRProvider, Depends(get_ocr)]

