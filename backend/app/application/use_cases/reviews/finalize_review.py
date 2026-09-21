"""
Finalize document review use case.
Marks human review completed, updates job status to COMPLETED at 100%,
and records audit logs.
"""

from datetime import datetime, timezone
from typing import Any
import uuid
import structlog

from app.application.use_cases.documents.exceptions import DocumentNotFoundError
from app.config.constants import JobStatus
from app.infrastructure.database.repositories.document_repository import DocumentRepository
from app.infrastructure.database.repositories.review_repository import ReviewRepository

logger = structlog.get_logger(__name__)


class FinalizeDocumentReviewUseCase:
    """Finalizes human review for a document and marks processing 100% complete."""

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
        reviewer_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        doc = await self._doc_repo.get_by_id(document_id)
        if not doc:
            raise DocumentNotFoundError(f"Documento con ID {document_id} no encontrado.")

        now = datetime.now(timezone.utc)

        # Update latest processing job
        job = await self._doc_repo.get_latest_job_for_document(document_id)
        if job:
            await self._doc_repo.update_processing_job(
                job_id=job.id,
                status=JobStatus.COMPLETED.value,
                current_step="review_completed",
                progress_pct=100,
            )

        await self._review_repo.record_audit_log(
            action="DOCUMENT_REVIEW_FINALIZED",
            resource="documents",
            user_id=reviewer_id,
            resource_id=document_id,
            details={
                "finalized_at": now.isoformat(),
            },
        )

        logger.info(
            "document_review_finalized",
            document_id=str(document_id),
            reviewer_id=str(reviewer_id) if reviewer_id else None,
        )

        return {
            "message": "Revisión humana finalizada y documento aprobado exitosamente",
            "document_id": document_id,
            "status": JobStatus.COMPLETED.value,
            "finalized_at": now,
        }
