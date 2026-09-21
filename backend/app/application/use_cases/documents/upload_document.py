"""
Upload document use case.

Handles validation, SHA-256 deduplication, page analysis via PyMuPDF,
file storage, database persistence, and initial processing job creation.
"""

import hashlib
import uuid
from datetime import datetime, timezone

import fitz  # PyMuPDF
import structlog

from app.application.interfaces.storage_provider import StorageProvider
from app.application.use_cases.documents.exceptions import (
    DuplicateDocumentError,
    FileTooLargeError,
    InvalidFileFormatError,
)
from app.config.constants import (
    MAX_PDF_PAGES,
    MIN_TEXT_CHARS_PER_PAGE,
    PDF_MAGIC_BYTES,
    AuditAction,
    DocumentType,
    JobStatus,
)
from app.config.settings import Settings, get_settings
from app.infrastructure.database.models.document_models import (
    Document,
    DocumentPage,
    ProcessingJob,
)
from app.infrastructure.database.repositories.document_repository import DocumentRepository
from app.infrastructure.database.repositories.user_repository import UserRepository

logger = structlog.get_logger(__name__)


class UploadDocumentUseCase:
    """Orchestrates secure upload and registration of a PDF resume."""

    def __init__(
        self,
        document_repo: DocumentRepository,
        user_repo: UserRepository,
        storage_provider: StorageProvider,
        settings: Settings | None = None,
    ) -> None:
        self._doc_repo = document_repo
        self._user_repo = user_repo
        self._storage = storage_provider
        self._settings = settings or get_settings()

    async def execute(
        self,
        file_bytes: bytes,
        filename: str,
        content_type: str | None,
        uploaded_by: uuid.UUID,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[Document, ProcessingJob]:
        """
        Execute document upload pipeline:
        1. Validate file size
        2. Validate content type and magic bytes
        3. Validate PDF readability and page count
        4. Calculate SHA-256 checksum and detect duplicates
        5. Store file in storage provider
        6. Persist Document and DocumentPage entities
        7. Create initial ProcessingJob with UPLOADED status
        8. Record audit log
        """
        # 1. Size validation
        file_size = len(file_bytes)
        if file_size == 0:
            raise InvalidFileFormatError("El archivo subido está vacío.")

        if file_size > self._settings.max_upload_size_bytes:
            raise FileTooLargeError(
                f"El archivo excede el tamaño máximo permitido de "
                f"{self._settings.max_upload_size_mb} MB."
            )

        # 2. Content type and magic bytes validation
        if content_type and "pdf" not in content_type.lower():
            raise InvalidFileFormatError(
                "Tipo de archivo no permitido. Solo se aceptan archivos PDF."
            )

        if not file_bytes.startswith(PDF_MAGIC_BYTES):
            raise InvalidFileFormatError(
                "El archivo no tiene una cabecera PDF válida (magic bytes no corresponden a %PDF)."
            )

        # 3. PDF readability, encryption, and page count check using PyMuPDF
        try:
            pdf_doc = fitz.open(stream=file_bytes, filetype="pdf")
        except Exception as exc:
            logger.warning("pdf_open_failed", filename=filename, error=str(exc))
            raise InvalidFileFormatError(
                "El archivo no es un documento PDF válido o está corrupto."
            ) from exc

        try:
            if pdf_doc.is_encrypted:
                raise InvalidFileFormatError(
                    "El archivo PDF está protegido con contraseña. Desproteja el documento antes de subirlo."
                )

            page_count = len(pdf_doc)
            if page_count == 0:
                raise InvalidFileFormatError("El archivo PDF no contiene ninguna página.")

            if page_count > MAX_PDF_PAGES:
                raise InvalidFileFormatError(
                    f"El documento tiene {page_count} páginas, excediendo el límite máximo de {MAX_PDF_PAGES} páginas."
                )

            # Analyze pages structure
            pages_data: list[dict[str, object]] = []
            for page_num in range(page_count):
                page = pdf_doc[page_num]
                rect = page.rect
                text = page.get_text().strip()
                has_text = len(text) >= MIN_TEXT_CHARS_PER_PAGE
                pages_data.append(
                    {
                        "page_number": page_num + 1,
                        "width_pts": float(rect.width),
                        "height_pts": float(rect.height),
                        "has_text": has_text,
                    }
                )
        finally:
            pdf_doc.close()

        # 4. SHA-256 Checksum calculation & Duplicate detection
        checksum_sha256 = hashlib.sha256(file_bytes).hexdigest()
        existing_doc = await self._doc_repo.get_by_checksum(checksum_sha256)
        if existing_doc is not None:
            logger.info(
                "duplicate_document_rejected",
                checksum=checksum_sha256,
                existing_id=str(existing_doc.id),
            )
            raise DuplicateDocumentError(
                message="Este documento ya ha sido subido al sistema previamente.",
                existing_document_id=existing_doc.id,
                existing_filename=existing_doc.original_filename,
            )

        # 5. Generate secure UUID-based storage key and store bytes
        now = datetime.now(timezone.utc)
        document_id = uuid.uuid4()
        storage_key = f"documents/{now.year:04d}/{now.month:02d}/{document_id}.pdf"

        await self._storage.save(file_bytes=file_bytes, key=storage_key)

        # 6. Create and persist Document record
        document = Document(
            id=document_id,
            storage_key=storage_key,
            original_filename=filename,
            file_size_bytes=file_size,
            mime_type="application/pdf",
            checksum_sha256=checksum_sha256,
            page_count=page_count,
            document_type=DocumentType.UNKNOWN.value,
            uploaded_by=uploaded_by,
        )
        created_document = await self._doc_repo.create_document(document)

        # Persist DocumentPages
        pages_to_create = [
            DocumentPage(
                document_id=document_id,
                page_number=int(p["page_number"]),
                width_pts=float(p["width_pts"]),
                height_pts=float(p["height_pts"]),
                has_text=bool(p["has_text"]),
            )
            for p in pages_data
        ]
        await self._doc_repo.create_document_pages(pages_to_create)

        # 7. Create initial ProcessingJob
        job = ProcessingJob(
            document_id=document_id,
            status=JobStatus.UPLOADED.value,
            progress_pct=0,
            current_step="ingestion",
            created_by=uploaded_by,
        )
        created_job = await self._doc_repo.create_processing_job(job)

        # 8. Record audit log
        try:
            await self._user_repo.create_audit_log(
                action=AuditAction.UPLOAD_DOCUMENT.value,
                user_id=uploaded_by,
                resource="documents",
                resource_id=document_id,
                ip_address=ip_address,
                user_agent=user_agent,
                details={
                    "original_filename": filename,
                    "file_size_bytes": file_size,
                    "page_count": page_count,
                    "checksum_sha256": checksum_sha256,
                    "storage_key": storage_key,
                    "job_id": str(created_job.id),
                },
            )
        except Exception as exc:
            logger.warning("audit_log_failed_on_upload", error=str(exc))

        logger.info(
            "document_uploaded_successfully",
            document_id=str(document_id),
            job_id=str(created_job.id),
            pages=page_count,
            size=file_size,
        )

        return created_document, created_job
