"""
Pipeline step for ATS resume extraction.
"""

import time
import structlog

from app.config.constants import DocumentType
from app.infrastructure.extraction.ats_extractor import AtsResumeExtractor
from app.infrastructure.extraction.pdf_text_extractor import PDFTextExtractor
from app.infrastructure.extraction.pipeline_context import ProcessingContext
from app.infrastructure.extraction.pipeline_step import PipelineStep

logger = structlog.get_logger(__name__)


class AtsExtractionStep(PipelineStep):
    """
    Executes structured field extraction for free-form ATS resumes.
    """

    def __init__(self, extractor: AtsResumeExtractor | None = None) -> None:
        self._extractor = extractor or AtsResumeExtractor()

    @property
    def step_name(self) -> str:
        return "ats_extraction"

    async def execute(self, context: ProcessingContext) -> ProcessingContext:
        if context.document_type != DocumentType.ATS:
            logger.info(
                "ats_step_skipped",
                document_id=str(context.document_id),
                document_type=context.document_type.value,
            )
            return context

        start_time = time.monotonic()
        logger.info(
            "ats_step_started",
            document_id=str(context.document_id),
        )

        full_text = ""
        page_texts: list[str] = []

        if context.ocr_result and context.ocr_result.pages:
            page_texts = [p.full_text for p in context.ocr_result.pages]
            full_text = "\n\n".join(page_texts)
        elif context.pdf_bytes:
            native_result = PDFTextExtractor.extract_native_document(context.pdf_bytes)
            page_texts = [p.full_text for p in native_result.pages]
            full_text = "\n\n".join(page_texts)

        canonical_resume = self._extractor.extract(full_text=full_text, page_texts=page_texts)

        context.canonical_resume = canonical_resume.to_dict()
        context.metadata["extracted_fields_count"] = len(canonical_resume.extracted_fields)
        context.metadata["skills_count"] = len(canonical_resume.metadata.get("skills", []))

        duration_ms = int((time.monotonic() - start_time) * 1000)
        context.mark_step_completed(self.step_name, duration_ms)

        logger.info(
            "ats_step_completed",
            document_id=str(context.document_id),
            duration_ms=duration_ms,
            fields_count=len(canonical_resume.extracted_fields),
        )
        return context
