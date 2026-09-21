"""
Get document by ID use case.
"""

import uuid
import structlog

from app.application.use_cases.documents.exceptions import DocumentNotFoundError
from app.infrastructure.database.models.document_models import Document, ProcessingJob
from app.infrastructure.database.repositories.document_repository import DocumentRepository

logger = structlog.get_logger(__name__)


class GetDocumentUseCase:
    """Retrieves document details and latest processing job."""

    def __init__(self, document_repo: DocumentRepository) -> None:
        self._doc_repo = document_repo

    async def execute(
        self, document_id: uuid.UUID
    ) -> tuple[Document, ProcessingJob | None]:
        doc = await self._doc_repo.get_by_id(document_id)
        if not doc:
            raise DocumentNotFoundError(f"Documento con ID {document_id} no encontrado.")

        latest_job = await self._doc_repo.get_latest_job_for_document(document_id)
        return doc, latest_job
