"""
Native PDF text extractor using PyMuPDF (fitz).

Extracts vector text, token coordinates (bounding boxes), and page dimensions.
Also provides page-to-image rendering for scanned/fallback pages.
"""

import time
import fitz  # PyMuPDF
import structlog

from app.application.interfaces.ocr_provider import (
    BoundingBox,
    OCRDocumentResult,
    OCRPageResult,
    OCRToken,
)
from app.config.constants import MIN_TEXT_CHARS_PER_PAGE, OCRProvider

logger = structlog.get_logger(__name__)


class PDFTextExtractor:
    """
    Extracts native text and tokens from digital PDFs with high performance.
    """

    def __init__(self, min_chars_per_page: int = MIN_TEXT_CHARS_PER_PAGE) -> None:
        self.min_chars_per_page = min_chars_per_page

    def extract_page(self, page: fitz.Page, page_number: int) -> OCRPageResult:
        """
        Extract text, tokens and bounding boxes from a single PyMuPDF Page.
        """
        full_text = page.get_text().strip()
        words_data = page.get_text("words")  # (x0, y0, x1, y1, word, block_no, line_no, word_no)

        tokens: list[OCRToken] = []
        for item in words_data:
            x0, y0, x1, y1, word = item[0], item[1], item[2], item[3], str(item[4])
            bbox = BoundingBox(
                x=float(x0),
                y=float(y0),
                width=float(x1 - x0),
                height=float(y1 - y0),
            )
            tokens.append(
                OCRToken(
                    text=word,
                    confidence=0.99,  # Native text has high fidelity
                    page_number=page_number,
                    bounding_box=bbox,
                )
            )

        has_native = len(full_text) >= self.min_chars_per_page
        confidence = 0.99 if has_native else 0.50

        return OCRPageResult(
            page_number=page_number,
            full_text=full_text,
            tokens=tokens,
            confidence=confidence,
            raw_response={
                "source": "native_pymupdf",
                "words_count": len(words_data),
            },
            width_pts=float(page.rect.width),
            height_pts=float(page.rect.height),
            has_native_text=has_native,
        )

    def extract_document(self, pdf_bytes: bytes) -> OCRDocumentResult:
        """
        Extract native text across all pages in a PDF document.
        """
        start_time = time.perf_counter()
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")

        try:
            pages_results: list[OCRPageResult] = []
            for page_idx in range(len(doc)):
                page = doc[page_idx]
                page_result = self.extract_page(page, page_number=page_idx + 1)
                pages_results.append(page_result)

            elapsed_ms = int((time.perf_counter() - start_time) * 1000)

            logger.info(
                "native_text_extracted",
                pages_count=len(pages_results),
                duration_ms=elapsed_ms,
            )

            return OCRDocumentResult(
                pages=pages_results,
                provider=OCRProvider.NATIVE.value,
                model_version="pymupdf-" + fitz.__version__,
                processing_ms=elapsed_ms,
            )
        finally:
            doc.close()

    def render_page_image(
        self, pdf_bytes: bytes, page_number: int, dpi: int = 150
    ) -> bytes:
        """
        Render a specific page to PNG image bytes for OCR or thumbnail preview.
        page_number is 1-indexed.
        """
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        try:
            if page_number < 1 or page_number > len(doc):
                raise ValueError(
                    f"Número de página inválido: {page_number}. El documento tiene {len(doc)} páginas."
                )

            page = doc[page_number - 1]
            pix = page.get_pixmap(dpi=dpi)
            return pix.tobytes("png")
        finally:
            doc.close()

    def has_scanned_pages(self, pdf_bytes: bytes) -> bool:
        """
        Returns True if any page lacks sufficient native text (requiring OCR).
        """
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        try:
            for page in doc:
                text = page.get_text().strip()
                if len(text) < self.min_chars_per_page:
                    return True
            return False
        finally:
            doc.close()
