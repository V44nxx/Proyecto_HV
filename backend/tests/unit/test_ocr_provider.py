"""
Unit tests for OCR data structures, MockOCRProvider, and factory.
"""

import pytest

from app.application.interfaces.ocr_provider import (
    BoundingBox,
    OCRDocumentResult,
    OCRPageResult,
    OCRToken,
)
from app.config.settings import OCRProviderName, Settings
from app.infrastructure.ocr.mock_ocr_provider import MockOCRProvider
from app.infrastructure.ocr.ocr_factory import get_ocr_provider


def test_bounding_box_to_dict() -> None:
    box = BoundingBox(x=10.1234, y=20.5678, width=100.999, height=45.556)
    d = box.to_dict()
    assert d["x"] == 10.12
    assert d["y"] == 20.57
    assert d["width"] == 101.0
    assert d["height"] == 45.56


def test_ocr_token_serialization() -> None:
    box = BoundingBox(x=5.0, y=10.0, width=50.0, height=12.0)
    token = OCRToken(text="Ingeniero", confidence=0.9876, page_number=1, bounding_box=box)
    d = token.to_dict()
    assert d["text"] == "Ingeniero"
    assert d["confidence"] == 0.9876
    assert d["page_number"] == 1
    assert d["bounding_box"] is not None
    assert d["bounding_box"]["x"] == 5.0


def test_ocr_document_result_properties() -> None:
    p1 = OCRPageResult(page_number=1, full_text="Página uno de hoja de vida", confidence=0.90)
    p2 = OCRPageResult(page_number=2, full_text="Página dos con experiencia laboral", confidence=0.80)

    doc_result = OCRDocumentResult(
        pages=[p1, p2],
        provider="TEST_PROVIDER",
        model_version="1.0.0",
        processing_ms=150,
    )

    assert doc_result.page_count == 2
    assert doc_result.overall_confidence == 0.85
    assert "Página uno" in doc_result.full_text
    assert "Página dos" in doc_result.full_text


@pytest.mark.asyncio
async def test_mock_ocr_provider_process_page() -> None:
    provider = MockOCRProvider(default_text="Nombre Carlos Gomez CC 123456", default_confidence=0.92)
    assert provider.provider_name == "MOCK"
    assert await provider.health_check() is True

    fake_image_bytes = b"\x89PNG\r\n\x1a\nfakeimagecontent"
    page_res = await provider.process_page(image_bytes=fake_image_bytes, page_number=1)

    assert page_res.page_number == 1
    assert page_res.full_text == "Nombre Carlos Gomez CC 123456"
    assert page_res.confidence == 0.92
    assert len(page_res.tokens) == 5
    assert page_res.tokens[0].text == "Nombre"
    assert page_res.tokens[0].bounding_box is not None


@pytest.mark.asyncio
async def test_mock_ocr_provider_process_document() -> None:
    provider = MockOCRProvider()
    doc_res = await provider.process_document(pdf_bytes=b"%PDF-1.4 mock")

    assert doc_res.page_count == 1
    assert doc_res.provider == "MOCK"
    assert doc_res.overall_confidence == 0.95


def test_ocr_factory_returns_mock() -> None:
    settings = Settings(
        ocr_provider=OCRProviderName.MOCK,
        secret_key="test-secret-key-at-least-32-chars-long",
        postgres_password="test_password",
    )
    provider = get_ocr_provider(settings)
    assert provider.provider_name == "MOCK"
