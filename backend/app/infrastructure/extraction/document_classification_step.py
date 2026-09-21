"""
Pipeline step for document classification.
Determines whether a document is FORMATO_UNICO, ATS, or UNKNOWN.
"""

import time
import structlog

from app.config.constants import DocumentType, JobStatus
from app.domain.services.document_classifier import DocumentClassifier
from app.infrastructure.extraction.pdf_text_extractor import PDFTextExtractor
from app.infrastructure.extraction.pipeline_context import ProcessingContext
from app.infrastructure.extraction.pipeline_step import PipelineStep

logger = structlog.get_logger(__name__)


class DocumentClassificationStep(PipelineStep):
    """
    Classifies the document using extracted text tokens from native PDF or OCR.
    """

    def __init__(self, classifier: DocumentClassifier | None = None) -> None:
        self._classifier = classifier or DocumentClassifier()

    @property
    def step_name(self) -> str:
        return "document_classification"

    async def execute(self, context: ProcessingContext) -> ProcessingContext:
        start_time = time.monotonic()
        logger.info(
            "classification_step_started",
            document_id=str(context.document_id),
        )

        # 1. Retrieve full text
        full_text = ""
        page_texts: list[str] = []

        if context.ocr_result and context.ocr_result.pages:
            page_texts = [p.full_text for p in context.ocr_result.pages]
            full_text = "\n\n".join(page_texts)
        elif context.pdf_bytes:
            native_result = PDFTextExtractor.extract_native_document(context.pdf_bytes)
            page_texts = [p.full_text for p in native_result.pages]
            full_text = "\n\n".join(page_texts)

        # 2. Run domain classifier
        classification_result = self._classifier.classify(
            text=full_text, page_texts=page_texts
        )

        # 3. Update processing context
        context.document_type = classification_result.document_type
        context.confidence_score = classification_result.confidence
        context.metadata["classification"] = classification_result.to_dict()

        if classification_result.document_type == DocumentType.UNKNOWN:
            context.status = JobStatus.REVIEW_REQUIRED
            context.error = "Tipo de formato no reconocido automáticamente; requiere revisión humana."
            context.error_type = "UNKNOWN_DOCUMENT_TYPE"
            logger.warn(
                "document_classified_unknown",
                document_id=str(context.document_id),
                confidence=classification_result.confidence,
                reasons=classification_result.reasons,
            )
        else:
            logger.info(
                "document_classified_success",
                document_id=str(context.document_id),
                document_type=classification_result.document_type.value,
                confidence=classification_result.confidence,
            )

        duration_ms = int((time.monotonic() - start_time) * 1000)
        context.mark_step_completed(self.step_name, duration_ms)
        return context
