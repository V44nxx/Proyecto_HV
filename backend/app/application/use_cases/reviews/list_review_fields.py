"""
List review fields use case.
"""

import uuid
import structlog

from app.application.use_cases.documents.exceptions import DocumentNotFoundError
from app.infrastructure.database.models.document_models import ExtractedField
from app.infrastructure.database.repositories.document_repository import DocumentRepository
from app.infrastructure.database.repositories.review_repository import ReviewRepository

logger = structlog.get_logger(__name__)


class ListReviewFieldsUseCase:
    """Retrieves all extracted fields for human review for a given document."""

    def __init__(
        self,
        document_repo: DocumentRepository,
        review_repo: ReviewRepository,
    ) -> None:
        self._doc_repo = document_repo
        self._review_repo = review_repo

    async def execute(
        self,
        document_id: uuid.UUID,
        status_filter: str | None = None,
        page_number: int | None = None,
    ) -> list[ExtractedField]:
        doc = await self._doc_repo.get_by_id(document_id)
        if not doc:
            raise DocumentNotFoundError(f"Documento con ID {document_id} no encontrado.")

        return await self._review_repo.get_fields_for_document(
            document_id=document_id,
            status_filter=status_filter,
            page_number=page_number,
        )
