"""
Deterministic Mock OCR provider for testing and local development.
"""

from typing import Any
import structlog

from app.application.interfaces.ocr_provider import (
    BoundingBox,
    OCRDocumentResult,
    OCRPageResult,
    OCRProvider,
    OCRToken,
)
from app.config.constants import OCRProvider as OCRProviderEnum

logger = structlog.get_logger(__name__)


class MockOCRProvider(OCRProvider):
    """
    Mock OCR provider that returns deterministic, configurable responses.
    Useful for unit testing, integration tests, and offline development.
    """

    def __init__(
        self,
        default_text: str = "TEXTO EXTRAIDO POR MOCK OCR PROVIDER",
        default_confidence: float = 0.95,
        healthy: bool = True,
    ) -> None:
        self.default_text = default_text
        self.default_confidence = default_confidence
        self.healthy = healthy

    @property
    def provider_name(self) -> str:
        return OCRProviderEnum.MOCK.value

    async def health_check(self) -> bool:
        return self.healthy

    async def process_page(
        self,
        image_bytes: bytes,
        page_number: int,
    ) -> OCRPageResult:
        """
        Produce a deterministic page result based on default_text.
        """
        words = self.default_text.split()
        tokens: list[OCRToken] = []

        # Generate fake bounding boxes across the page
        cur_x = 50.0
        cur_y = 50.0
        for word in words:
            width = len(word) * 8.0
            tokens.append(
                OCRToken(
                    text=word,
                    confidence=self.default_confidence,
                    page_number=page_number,
                    bounding_box=BoundingBox(
                        x=cur_x,
                        y=cur_y,
                        width=width,
                        height=14.0,
                    ),
                )
            )
            cur_x += width + 10.0
            if cur_x > 500.0:
                cur_x = 50.0
                cur_y += 20.0

        return OCRPageResult(
            page_number=page_number,
            full_text=self.default_text,
            tokens=tokens,
            confidence=self.default_confidence,
            raw_response={"mock": True, "image_size_bytes": len(image_bytes)},
            width_pts=595.0,
            height_pts=842.0,
            has_native_text=False,
        )

    async def process_document(
        self,
        pdf_bytes: bytes,
    ) -> OCRDocumentResult:
        """
        Produce a deterministic document result with 1 page.
        """
        page_res = await self.process_page(image_bytes=pdf_bytes[:100], page_number=1)
        return OCRDocumentResult(
            pages=[page_res],
            provider=self.provider_name,
            model_version="mock-v1",
            processing_ms=10,
        )
