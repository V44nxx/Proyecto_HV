"""
Azure Document Intelligence OCR provider adapter.
"""

from typing import Any
import structlog

from app.application.interfaces.ocr_provider import (
    OCRDocumentResult,
    OCRPageResult,
    OCRProvider,
    OCRProviderUnavailableError,
)
from app.config.constants import OCRProvider as OCRProviderEnum
from app.config.settings import Settings, get_settings

logger = structlog.get_logger(__name__)


class AzureDocumentIntelligenceProvider(OCRProvider):
    """
    Adapter for Azure AI Document Intelligence.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    @property
    def provider_name(self) -> str:
        return OCRProviderEnum.AZURE_DI.value

    async def health_check(self) -> bool:
        return bool(
            self._settings.azure_document_intelligence_endpoint
            and self._settings.azure_document_intelligence_key
        )

    def _ensure_configured(self) -> None:
        if not (
            self._settings.azure_document_intelligence_endpoint
            and self._settings.azure_document_intelligence_key
        ):
            raise OCRProviderUnavailableError(
                "Azure Document Intelligence no está configurado. "
                "Defina AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT y AZURE_DOCUMENT_INTELLIGENCE_KEY."
            )

    async def process_page(
        self,
        image_bytes: bytes,
        page_number: int,
    ) -> OCRPageResult:
        self._ensure_configured()
        raise NotImplementedError("Azure Document Intelligence page processing")

    async def process_document(
        self,
        pdf_bytes: bytes,
    ) -> OCRDocumentResult:
        self._ensure_configured()
        raise NotImplementedError("Azure Document Intelligence document processing")
