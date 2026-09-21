"""
API integration tests for document endpoints (/api/v1/documents).
"""

import io
import uuid
import fitz  # PyMuPDF
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.session import get_db_session
from app.infrastructure.storage.local_storage import LocalStorageProvider
from app.main import create_application
from app.presentation.dependencies.auth import (
    AuthenticatedUser,
    get_current_user,
)
from app.presentation.dependencies.document_dependencies import get_storage


def make_test_pdf(text: str = "Hoja de Vida de Prueba - Carlos Gomez", pages: int = 1) -> bytes:
    doc = fitz.open()
    for i in range(pages):
        page = doc.new_page(width=595, height=842)
        page.insert_text((50, 72), f"{text} - Página {i + 1}")
    pdf_bytes = doc.write()
    doc.close()
    return pdf_bytes


@pytest_asyncio.fixture
async def document_api_client(test_db: AsyncSession, tmp_path):
    """
    Client configured with test database, temporary storage,
    and an authenticated user with full document permissions.
    """
    app = create_application()

    # In-memory DB
    app.dependency_overrides[get_db_session] = lambda: test_db

    # Temp storage
    test_storage = LocalStorageProvider(base_path=tmp_path)
    app.dependency_overrides[get_storage] = lambda: test_storage

    # Full document permissions
    test_user = AuthenticatedUser(
        user_id=str(uuid.uuid4()),
        role="GESTOR",
        permissions=["documents:read", "documents:write", "documents:delete"],
        jti="test-jti-123",
    )
    app.dependency_overrides[get_current_user] = lambda: test_user

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


@pytest_asyncio.fixture
async def unprivileged_client(test_db: AsyncSession, tmp_path):
    """
    Client with a user lacking documents:write and documents:delete.
    """
    app = create_application()
    app.dependency_overrides[get_db_session] = lambda: test_db
    test_storage = LocalStorageProvider(base_path=tmp_path)
    app.dependency_overrides[get_storage] = lambda: test_storage

    read_only_user = AuthenticatedUser(
        user_id=str(uuid.uuid4()),
        role="CONSULTOR",
        permissions=["documents:read"],
        jti="test-jti-456",
    )
    app.dependency_overrides[get_current_user] = lambda: read_only_user

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.mark.asyncio
async def test_upload_document_requires_write_permission(
    unprivileged_client: AsyncClient,
) -> None:
    pdf_bytes = make_test_pdf()
    files = {"file": ("test.pdf", io.BytesIO(pdf_bytes), "application/pdf")}

    response = await unprivileged_client.post("/api/v1/documents", files=files)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_upload_valid_pdf_success(
    document_api_client: AsyncClient,
) -> None:
    pdf_bytes = make_test_pdf(pages=2)
    files = {"file": ("carlos_gomez_cv.pdf", io.BytesIO(pdf_bytes), "application/pdf")}

    response = await document_api_client.post("/api/v1/documents", files=files)
    assert response.status_code == 201

    data = response.json()
    assert "document" in data
    assert "job" in data
    doc = data["document"]
    assert doc["original_filename"] == "carlos_gomez_cv.pdf"
    assert doc["page_count"] == 2
    assert doc["file_size_bytes"] == len(pdf_bytes)
    assert data["job"]["status"] == "UPLOADED"


@pytest.mark.asyncio
async def test_upload_duplicate_pdf_returns_409(
    document_api_client: AsyncClient,
) -> None:
    pdf_bytes = make_test_pdf()
    files1 = {"file": ("original.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    resp1 = await document_api_client.post("/api/v1/documents", files=files1)
    assert resp1.status_code == 201

    files2 = {"file": ("duplicate.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    resp2 = await document_api_client.post("/api/v1/documents", files=files2)
    assert resp2.status_code == 409
    data = resp2.json()
    assert "detail" in data
    assert "existing_document_id" in data["detail"]


@pytest.mark.asyncio
async def test_list_documents(
    document_api_client: AsyncClient,
) -> None:
    # Upload one doc first
    pdf_bytes = make_test_pdf()
    files = {"file": ("list_test.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    await document_api_client.post("/api/v1/documents", files=files)

    response = await document_api_client.get("/api/v1/documents")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 1
    assert data["page"] == 1


@pytest.mark.asyncio
async def test_get_document_detail_and_job(
    document_api_client: AsyncClient,
) -> None:
    pdf_bytes = make_test_pdf()
    files = {"file": ("detail_test.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    upload_resp = await document_api_client.post("/api/v1/documents", files=files)
    doc_id = upload_resp.json()["document"]["id"]

    # Get detail
    detail_resp = await document_api_client.get(f"/api/v1/documents/{doc_id}")
    assert detail_resp.status_code == 200
    data = detail_resp.json()
    assert data["document"]["id"] == doc_id
    assert data["latest_job"] is not None
    assert data["latest_job"]["document_id"] == doc_id

    # Get job endpoint
    job_resp = await document_api_client.get(f"/api/v1/documents/{doc_id}/job")
    assert job_resp.status_code == 200
    assert job_resp.json()["document_id"] == doc_id


@pytest.mark.asyncio
async def test_download_document_file(
    document_api_client: AsyncClient,
) -> None:
    pdf_bytes = make_test_pdf()
    files = {"file": ("download_me.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    upload_resp = await document_api_client.post("/api/v1/documents", files=files)
    doc_id = upload_resp.json()["document"]["id"]

    download_resp = await document_api_client.get(f"/api/v1/documents/{doc_id}/file")
    assert download_resp.status_code == 200
    assert download_resp.headers["content-type"] == "application/pdf"
    assert download_resp.content == pdf_bytes


@pytest.mark.asyncio
async def test_delete_document_soft_delete(
    document_api_client: AsyncClient,
) -> None:
    pdf_bytes = make_test_pdf()
    files = {"file": ("delete_me.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    upload_resp = await document_api_client.post("/api/v1/documents", files=files)
    doc_id = upload_resp.json()["document"]["id"]

    # Delete
    del_resp = await document_api_client.delete(f"/api/v1/documents/{doc_id}")
    assert del_resp.status_code == 204

    # Subsequent GET returns 404
    get_resp = await document_api_client.get(f"/api/v1/documents/{doc_id}")
    assert get_resp.status_code == 404
