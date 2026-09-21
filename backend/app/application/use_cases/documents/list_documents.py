"""
List documents use case with pagination and filters.
"""

import uuid
from app.infrastructure.database.models.document_models import Document
from app.infrastructure.database.repositories.document_repository import DocumentRepository


class ListDocumentsUseCase:
    """Lists documents with pagination and optional filters."""

    def __init__(self, document_repo: DocumentRepository) -> None:
        self._doc_repo = document_repo

    async def execute(
        self,
        page: int = 1,
        page_size: int = 20,
        document_type: str | None = None,
        person_id: uuid.UUID | None = None,
    ) -> tuple[list[Document], int]:
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 20
        if page_size > 100:
            page_size = 100

        skip = (page - 1) * page_size
        return await self._doc_repo.list_documents(
            skip=skip,
            limit=page_size,
            document_type=document_type,
            person_id=person_id,
        )
