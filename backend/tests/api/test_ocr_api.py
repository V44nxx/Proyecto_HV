"""
API tests for OCR health check and document text processing endpoints.
"""

import io
import uuid
import fitz
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.session import get_db_session
from app.infrastructure.ocr.mock_ocr_provider import MockOCRProvider
from app.infrastructure.storage.local_storage import LocalStorageProvider
from app.main import create_application
from app.presentation.dependencies.auth import (
    AuthenticatedUser,
    get_current_user,
)
from app.presentation.dependencies.document_dependencies import (
    get_ocr,
    get_storage,
)


def make_pdf(text: str = "Hoja de vida para pruebas OCR y PyMuPDF") -> bytes:
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 72), text)
    pdf_bytes = doc.write()
    doc.close()
    return pdf_bytes


@pytest_asyncio.fixture
async def ocr_api_client(test_db: AsyncSession, tmp_path):
    app = create_application()

    # DB override
    app.dependency_overrides[get_db_session] = lambda: test_db

    # Storage override
    test_storage = LocalStorageProvider(base_path=tmp_path)
    app.dependency_overrides[get_storage] = lambda: test_storage

    # Mock OCR provider override
    mock_ocr = MockOCRProvider()
    app.dependency_overrides[get_ocr] = lambda: mock_ocr

    # Authenticated user with documents:write and documents:read
    test_user = AuthenticatedUser(
        user_id=str(uuid.uuid4()),
        role="GESTOR",
        permissions=["documents:read", "documents:write"],
        jti="ocr-test-jti",
    )
    app.dependency_overrides[get_current_user] = lambda: test_user

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.mark.asyncio
async def test_health_check_ocr_returns_ok(ocr_api_client: AsyncClient) -> None:
    response = await ocr_api_client.get("/api/v1/health/ocr")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "provider" in data
    assert data["healthy"] is True


@pytest.mark.asyncio
async def test_process_document_text_endpoint(ocr_api_client: AsyncClient) -> None:
    # 1. Upload a document first
    pdf_bytes = make_pdf(
        "Carlos Gomez Rodriguez - Ingeniero de Sistemas y Desarrollador Fullstack Bogota Colombia "
        "con mas de diez anos de experiencia profesional en desarrollo de software."
    )
    files = {"file": ("extract_test.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    upload_resp = await ocr_api_client.post("/api/v1/documents", files=files)
    assert upload_resp.status_code == 201
    doc_id = upload_resp.json()["document"]["id"]

    # 2. Trigger text extraction
    process_resp = await ocr_api_client.post(f"/api/v1/documents/{doc_id}/process-text")
    assert process_resp.status_code == 200
    data = process_resp.json()
    assert data["document_id"] == doc_id
    assert data["pages_count"] == 1
    assert "Carlos Gomez" in data["full_text_preview"]

    # 3. Check extractions endpoint
    extractions_resp = await ocr_api_client.get(f"/api/v1/documents/{doc_id}/extractions")
    assert extractions_resp.status_code == 200
    extractions = extractions_resp.json()
    assert len(extractions) == 1
    assert extractions[0]["document_id"] == doc_id
    assert "Carlos Gomez" in extractions[0]["raw_text"]
