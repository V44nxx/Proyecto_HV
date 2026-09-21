"""
Soft-delete document use case.
"""

import uuid
import structlog

from app.application.use_cases.documents.exceptions import DocumentNotFoundError
from app.config.constants import AuditAction
from app.infrastructure.database.repositories.document_repository import DocumentRepository
from app.infrastructure.database.repositories.user_repository import UserRepository

logger = structlog.get_logger(__name__)


class DeleteDocumentUseCase:
    """Soft-deletes a document and records an audit log entry."""

    def __init__(
        self,
        document_repo: DocumentRepository,
        user_repo: UserRepository,
    ) -> None:
        self._doc_repo = document_repo
        self._user_repo = user_repo

    async def execute(
        self,
        document_id: uuid.UUID,
        deleted_by: uuid.UUID,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> bool:
        doc = await self._doc_repo.get_by_id(document_id)
        if not doc:
            raise DocumentNotFoundError(f"Documento con ID {document_id} no encontrado.")

        success = await self._doc_repo.soft_delete(document_id)
        if success:
            try:
                await self._user_repo.create_audit_log(
                    action=AuditAction.DELETE_DOCUMENT.value,
                    user_id=deleted_by,
                    resource="documents",
                    resource_id=document_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    details={
                        "original_filename": doc.original_filename,
                        "storage_key": doc.storage_key,
                    },
                )
            except Exception as exc:
                logger.warning("audit_log_failed_on_delete", error=str(exc))

        return success
