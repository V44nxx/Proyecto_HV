"""
OCR Provider interface and common data structures.

This port defines the abstract contract for document and page level OCR
and text extraction services. The core domain never depends on a specific OCR vendor.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


class OCRError(Exception):
    """Base exception for OCR and document text extraction errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class OCRProviderUnavailableError(OCRError):
    """Raised when the configured OCR service cannot be reached or credentials fail."""
    pass


class OCRProcessingError(OCRError):
    """Raised when an OCR processing operation fails on a document or page."""
    pass


@dataclass(frozen=True)
class BoundingBox:
    """
    Coordinates of an extracted token or text block in points (1/72 inch).
    Origin (0,0) is top-left of the page.
    """
    x: float
    y: float
    width: float
    height: float

    def to_dict(self) -> dict[str, float]:
        return {
            "x": round(self.x, 2),
            "y": round(self.y, 2),
            "width": round(self.width, 2),
            "height": round(self.height, 2),
        }


@dataclass(frozen=True)
class OCRToken:
    """Individual word or token extracted with confidence and bounding box."""
    text: str
    confidence: float
    page_number: int
    bounding_box: BoundingBox | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "confidence": round(self.confidence, 4),
            "page_number": self.page_number,
            "bounding_box": self.bounding_box.to_dict() if self.bounding_box else None,
        }


@dataclass(frozen=True)
class OCRPageResult:
    """Extracted text, tokens, and geometry for a single document page."""
    page_number: int
    full_text: str
    tokens: list[OCRToken] = field(default_factory=list)
    confidence: float = 1.0
    raw_response: dict[str, Any] = field(default_factory=dict)
    width_pts: float = 0.0
    height_pts: float = 0.0
    has_native_text: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "page_number": self.page_number,
            "full_text": self.full_text,
            "tokens_count": len(self.tokens),
            "confidence": round(self.confidence, 4),
            "width_pts": round(self.width_pts, 2),
            "height_pts": round(self.height_pts, 2),
            "has_native_text": self.has_native_text,
        }


@dataclass(frozen=True)
class OCRDocumentResult:
    """Complete extraction result for a multi-page document."""
    pages: list[OCRPageResult]
    provider: str
    model_version: str = "1.0.0"
    processing_ms: int = 0

    @property
    def full_text(self) -> str:
        """Concatenated full text across all pages separated by double newlines."""
        return "\n\n".join(p.full_text for p in self.pages if p.full_text.strip())

    @property
    def overall_confidence(self) -> float:
        """Average confidence across all pages."""
        if not self.pages:
            return 0.0
        return round(sum(p.confidence for p in self.pages) / len(self.pages), 4)

    @property
    def page_count(self) -> int:
        return len(self.pages)

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "model_version": self.model_version,
            "processing_ms": self.processing_ms,
            "page_count": self.page_count,
            "overall_confidence": round(self.overall_confidence, 4),
            "pages": [p.to_dict() for p in self.pages],
        }


class OCRProvider(ABC):
    """
    Abstract interface for OCR and document AI providers.
    """

    @abstractmethod
    async def process_page(
        self,
        image_bytes: bytes,
        page_number: int,
    ) -> OCRPageResult:
        """
        Run OCR on rendered page image bytes.
        """
        ...

    @abstractmethod
    async def process_document(
        self,
        pdf_bytes: bytes,
    ) -> OCRDocumentResult:
        """
        Run OCR on an entire PDF document.
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Verify provider accessibility and credentials.
        """
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """
        Returns the unique identifier of this provider.
        """
        ...
