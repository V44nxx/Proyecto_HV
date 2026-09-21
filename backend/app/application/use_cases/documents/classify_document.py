"""
Classify document use case.

Executes document classification to determine if a document is FORMATO_UNICO,
ATS, or UNKNOWN, updating the Document entity and ProcessingJob tracking.
"""

from datetime import datetime, timezone
import uuid
import structlog

from app.application.interfaces.storage_provider import StorageProvider
from app.application.use_cases.documents.exceptions import DocumentNotFoundError
from app.config.constants import DocumentType, JobStatus
from app.domain.services.document_classifier import DocumentClassifier
from app.domain.value_objects.classification_result import ClassificationResult
from app.infrastructure.database.repositories.document_repository import DocumentRepository
from app.infrastructure.extraction.pdf_text_extractor import PDFTextExtractor

logger = structlog.get_logger(__name__)


class ClassifyDocumentUseCase:
    """
    Classifies a document based on extracted text tokens.
    """

    def __init__(
        self,
        document_repo: DocumentRepository,
        storage_provider: StorageProvider,
        classifier: DocumentClassifier | None = None,
    ) -> None:
        self._doc_repo = document_repo
        self._storage = storage_provider
        self._classifier = classifier or DocumentClassifier()

    async def execute(
        self,
        document_id: uuid.UUID,
        job_id: uuid.UUID | None = None,
    ) -> ClassificationResult:
        doc = await self._doc_repo.get_by_id(document_id)
        if not doc:
            raise DocumentNotFoundError(f"Documento con ID {document_id} no encontrado.")

        # Resolve processing job
        job = None
        if job_id:
            job = await self._doc_repo.get_processing_job(job_id)
        if not job:
            job = await self._doc_repo.get_latest_job_for_document(document_id)

        # 1. Gather text: from extractions table or fallback to native PDF extractor
        extractions = await self._doc_repo.get_extractions_for_document(document_id)
        full_text = ""
        page_texts: list[str] = []

        if extractions:
            page_texts = [e.raw_text for e in extractions]
            full_text = "\n\n".join(page_texts)
        else:
            pdf_bytes = await self._storage.get(doc.storage_key)
            native_res = PDFTextExtractor.extract_native_document(pdf_bytes)
            page_texts = [p.full_text for p in native_res.pages]
            full_text = "\n\n".join(page_texts)

        # 2. Run domain classifier
        classification_result = self._classifier.classify(
            text=full_text, page_texts=page_texts
        )

        # 3. Update document type in repository
        await self._doc_repo.update_document_type(
            document_id=document_id,
            document_type=classification_result.document_type.value,
        )

        # 4. Update job status
        if job:
            now = datetime.now(timezone.utc)
            if classification_result.document_type == DocumentType.UNKNOWN:
                await self._doc_repo.update_processing_job(
                    job_id=job.id,
                    status=JobStatus.REVIEW_REQUIRED.value,
                    current_step="document_classification",
                    progress_pct=45,
                    error_type="UNKNOWN_DOCUMENT_TYPE",
                    error_message="El formato del documento no pudo identificarse como Formato Único o ATS. Requiere revisión manual.",
                )
            else:
                await self._doc_repo.update_processing_job(
                    job_id=job.id,
                    status=JobStatus.PROCESSING.value,
                    current_step="document_classification",
                    progress_pct=45,
                )

        logger.info(
            "document_classification_completed",
            document_id=str(document_id),
            document_type=classification_result.document_type.value,
            confidence=classification_result.confidence,
        )

        return classification_result
