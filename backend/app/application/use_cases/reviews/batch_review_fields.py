"""
Batch review fields use case.
"""

import uuid
import structlog

from app.application.use_cases.documents.exceptions import DocumentNotFoundError
from app.config.constants import ReviewStatus
from app.infrastructure.database.repositories.document_repository import DocumentRepository
from app.infrastructure.database.repositories.review_repository import ReviewRepository

logger = structlog.get_logger(__name__)


class BatchReviewFieldsUseCase:
    """Handles bulk approval or rejection of extracted fields."""

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
        field_ids: list[uuid.UUID],
        action: str,
        reviewer_id: uuid.UUID | None = None,
    ) -> int:
        doc = await self._doc_repo.get_by_id(document_id)
        if not doc:
            raise DocumentNotFoundError(f"Documento con ID {document_id} no encontrado.")

        status = ReviewStatus.ACCEPTED.value if action.upper() == "ACCEPT" else ReviewStatus.REJECTED.value

        updated_count = await self._review_repo.batch_update_status(
            field_ids=field_ids,
            review_status=status,
            reviewer_id=reviewer_id,
        )

        await self._review_repo.record_audit_log(
            action="BATCH_FIELDS_REVIEWED",
            resource="extracted_fields",
            user_id=reviewer_id,
            resource_id=document_id,
            details={
                "action": action.upper(),
                "fields_count": updated_count,
                "field_ids": [str(f) for f in field_ids],
            },
        )

        return updated_count
