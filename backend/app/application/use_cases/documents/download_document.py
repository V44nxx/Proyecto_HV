"""
Download / retrieve original document file use case.
"""

import uuid
import structlog

from app.application.interfaces.storage_provider import StorageProvider
from app.application.use_cases.documents.exceptions import DocumentNotFoundError
from app.config.constants import AuditAction
from app.infrastructure.database.repositories.document_repository import DocumentRepository
from app.infrastructure.database.repositories.user_repository import UserRepository

logger = structlog.get_logger(__name__)


class DownloadDocumentUseCase:
    """Retrieves original PDF file content from storage with audit tracking."""

    def __init__(
        self,
        document_repo: DocumentRepository,
        user_repo: UserRepository,
        storage_provider: StorageProvider,
    ) -> None:
        self._doc_repo = document_repo
        self._user_repo = user_repo
        self._storage = storage_provider

    async def execute(
        self,
        document_id: uuid.UUID,
        requested_by: uuid.UUID,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[bytes, str, str]:
        """
        Retrieves file bytes, original filename, and mime type.
        """
        doc = await self._doc_repo.get_by_id(document_id)
        if not doc:
            raise DocumentNotFoundError(f"Documento con ID {document_id} no encontrado.")

        file_bytes = await self._storage.get(doc.storage_key)

        try:
            await self._user_repo.create_audit_log(
                action=AuditAction.VIEW_DOCUMENT.value,
                user_id=requested_by,
                resource="documents",
                resource_id=document_id,
                ip_address=ip_address,
                user_agent=user_agent,
                details={"filename": doc.original_filename},
            )
        except Exception as exc:
            logger.warning("audit_log_failed_on_download", error=str(exc))

        return file_bytes, doc.original_filename, doc.mime_type
