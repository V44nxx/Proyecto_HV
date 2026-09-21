"""
Text extraction pipeline step.

Coordinates native PyMuPDF text extraction with OCR provider fallback
for image-only / scanned pages.
"""

import time
import structlog

from app.application.interfaces.ocr_provider import (
    OCRDocumentResult,
    OCRPageResult,
    OCRProvider,
)
from app.config.constants import JobStatus
from app.infrastructure.extraction.pdf_text_extractor import PDFTextExtractor
from app.infrastructure.extraction.pipeline_context import ProcessingContext
from app.infrastructure.extraction.pipeline_step import PipelineStep

logger = structlog.get_logger(__name__)


class TextExtractionStep(PipelineStep):
    """
    Extracts text from PDF pages.
    Employs native PyMuPDF extraction for digital text and invokes the OCR provider
    for pages lacking native text (scanned documents or raster images).
    """

    def __init__(
        self,
        ocr_provider: OCRProvider,
        text_extractor: PDFTextExtractor | None = None,
    ) -> None:
        self.ocr_provider = ocr_provider
        self.text_extractor = text_extractor or PDFTextExtractor()

    @property
    def step_name(self) -> str:
        return "text_extraction"

    async def execute(self, context: ProcessingContext) -> ProcessingContext:
        start_time = time.perf_counter()
        logger.info(
            "text_extraction_started",
            document_id=str(context.document_id),
            ocr_provider=self.ocr_provider.provider_name,
        )

        # 1. First run native extraction
        native_doc_result = self.text_extractor.extract_document(context.pdf_bytes)

        # 2. Check each page: if it lacks native text, apply OCR
        final_pages: list[OCRPageResult] = []
        hybrid_ocr_used = False

        for page_res in native_doc_result.pages:
            if page_res.has_native_text:
                final_pages.append(page_res)
            else:
                hybrid_ocr_used = True
                logger.info(
                    "page_lacks_native_text_running_ocr",
                    document_id=str(context.document_id),
                    page_number=page_res.page_number,
                )
                # Render page to PNG image and run OCR
                image_bytes = self.text_extractor.render_page_image(
                    pdf_bytes=context.pdf_bytes,
                    page_number=page_res.page_number,
                )
                ocr_page = await self.ocr_provider.process_page(
                    image_bytes=image_bytes,
                    page_number=page_res.page_number,
                )
                final_pages.append(ocr_page)

        total_duration_ms = int((time.perf_counter() - start_time) * 1000)

        # Build consolidated OCRDocumentResult
        provider_label = (
            f"HYBRID({self.ocr_provider.provider_name})"
            if hybrid_ocr_used
            else native_doc_result.provider
        )

        consolidated_result = OCRDocumentResult(
            pages=final_pages,
            provider=provider_label,
            model_version=native_doc_result.model_version,
            processing_ms=total_duration_ms,
        )

        context.ocr_result = consolidated_result
        context.status = JobStatus.OCR_COMPLETED
        context.mark_step_completed(self.step_name, duration_ms=total_duration_ms)

        logger.info(
            "text_extraction_completed",
            document_id=str(context.document_id),
            pages=len(final_pages),
            hybrid=hybrid_ocr_used,
            duration_ms=total_duration_ms,
        )

        return context
