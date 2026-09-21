"""
OCR Provider factory.

Provides the configured OCRProvider instance based on system settings.
"""

import structlog

from app.application.interfaces.ocr_provider import OCRProvider
from app.config.settings import OCRProviderName, Settings, get_settings
from app.infrastructure.ocr.azure_document_intelligence import AzureDocumentIntelligenceProvider
from app.infrastructure.ocr.google_document_ai import GoogleDocumentAIProvider
from app.infrastructure.ocr.mock_ocr_provider import MockOCRProvider

logger = structlog.get_logger(__name__)


def get_ocr_provider(settings: Settings | None = None) -> OCRProvider:
    """
    Returns the active OCRProvider instance based on settings.
    """
    if settings is None:
        settings = get_settings()

    provider_enum = settings.ocr_provider

    if provider_enum == OCRProviderName.GOOGLE_DAI:
        return GoogleDocumentAIProvider(settings=settings)
    elif provider_enum == OCRProviderName.AZURE_DI:
        return AzureDocumentIntelligenceProvider(settings=settings)
    else:
        return MockOCRProvider()
