"""
Process document text extraction use case.

Executes native extraction and OCR fallback, persisting DocumentExtraction
records and updating the ProcessingJob state.
"""

from datetime import datetime, timezone
import uuid
import structlog

from app.application.interfaces.ocr_provider import OCRDocumentResult, OCRProvider
from app.application.interfaces.storage_provider import StorageProvider
from app.application.use_cases.documents.exceptions import DocumentNotFoundError
from app.config.constants import JobStatus
from app.infrastructure.database.models.document_models import DocumentExtraction
from app.infrastructure.database.repositories.document_repository import DocumentRepository
from app.infrastructure.extraction.pipeline_context import ProcessingContext
from app.infrastructure.extraction.text_extraction_step import TextExtractionStep

logger = structlog.get_logger(__name__)


class ProcessDocumentTextUseCase:
    """
    Coordinates text extraction and OCR processing for a document.
    """

    def __init__(
        self,
        document_repo: DocumentRepository,
        storage_provider: StorageProvider,
        ocr_provider: OCRProvider,
    ) -> None:
        self._doc_repo = document_repo
        self._storage = storage_provider
        self._ocr_provider = ocr_provider
        self._extraction_step = TextExtractionStep(ocr_provider=ocr_provider)

    async def execute(
        self,
        document_id: uuid.UUID,
        job_id: uuid.UUID | None = None,
    ) -> OCRDocumentResult:
        doc = await self._doc_repo.get_by_id(document_id)
        if not doc:
            raise DocumentNotFoundError(f"Documento con ID {document_id} no encontrado.")

        # Resolve or fetch active job
        job = None
        if job_id:
            job = await self._doc_repo.get_processing_job(job_id)
        if not job:
            job = await self._doc_repo.get_latest_job_for_document(document_id)

        now = datetime.now(timezone.utc)
        if job:
            await self._doc_repo.update_processing_job(
                job_id=job.id,
                status=JobStatus.PROCESSING.value,
                current_step="text_extraction",
                progress_pct=15,
                started_at=job.started_at or now,
            )

        # Retrieve file bytes from storage
        pdf_bytes = await self._storage.get(doc.storage_key)

        # Build pipeline context
        context = ProcessingContext(
            document_id=document_id,
            pdf_bytes=pdf_bytes,
            job_id=job.id if job else None,
        )

        # Run extraction step
        context = await self._extraction_step.execute(context)
        ocr_result = context.ocr_result

        if not ocr_result:
            raise RuntimeError("La extracción de texto no produjo ningún resultado.")

        # Load document pages to link page IDs
        existing_pages = await self._doc_repo.list_document_pages(document_id)
        page_map = {p.page_number: p.id for p in existing_pages}

        # Persist DocumentExtraction records per page
        extractions_to_save: list[DocumentExtraction] = []
        for p in ocr_result.pages:
            page_id = page_map.get(p.page_number)
            extractions_to_save.append(
                DocumentExtraction(
                    document_id=document_id,
                    page_id=page_id,
                    ocr_provider=ocr_result.provider,
                    raw_text=p.full_text,
                    extraction_data=p.to_dict(),
                    confidence=p.confidence,
                    processing_ms=ocr_result.processing_ms,
                    model_version=ocr_result.model_version,
                )
            )

        if extractions_to_save:
            await self._doc_repo.create_document_extractions(extractions_to_save)

        # Update processing job to OCR_COMPLETED
        if job:
            await self._doc_repo.update_processing_job(
                job_id=job.id,
                status=JobStatus.OCR_COMPLETED.value,
                current_step="ocr_completed",
                progress_pct=30,
            )

        logger.info(
            "document_text_processing_completed",
            document_id=str(document_id),
            pages_count=len(ocr_result.pages),
            overall_confidence=ocr_result.overall_confidence,
        )

        return ocr_result
