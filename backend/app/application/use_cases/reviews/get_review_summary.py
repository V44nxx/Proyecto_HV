"""
Get review summary use case.
"""

from typing import Any
import uuid
import structlog

from app.application.use_cases.documents.exceptions import DocumentNotFoundError
from app.infrastructure.database.repositories.document_repository import DocumentRepository
from app.infrastructure.database.repositories.review_repository import ReviewRepository

logger = structlog.get_logger(__name__)


class GetReviewSummaryUseCase:
    """Calculates review progress and metrics for a document's extracted fields."""

    def __init__(
        self,
        document_repo: DocumentRepository,
        review_repo: ReviewRepository,
    ) -> None:
        self._doc_repo = document_repo
        self._review_repo = review_repo

    async def execute(self, document_id: uuid.UUID) -> dict[str, Any]:
        doc = await self._doc_repo.get_by_id(document_id)
        if not doc:
            raise DocumentNotFoundError(f"Documento con ID {document_id} no encontrado.")

        summary = await self._review_repo.get_review_summary(document_id)
        summary["document_id"] = document_id
        return summary
