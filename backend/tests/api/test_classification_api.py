"""
API tests for document classification endpoints:
- POST /api/v1/documents/{id}/classify
- GET  /api/v1/documents/{id}/classification
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


def make_pdf(text: str) -> bytes:
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 72), text)
    pdf_bytes = doc.write()
    doc.close()
    return pdf_bytes


@pytest_asyncio.fixture
async def classification_api_client(test_db: AsyncSession, tmp_path):
    app = create_application()

    # DB override
    app.dependency_overrides[get_db_session] = lambda: test_db

    # Storage override
    test_storage = LocalStorageProvider(base_path=tmp_path)
    app.dependency_overrides[get_storage] = lambda: test_storage

    # Mock OCR override
    app.dependency_overrides[get_ocr] = lambda: MockOCRProvider()

    # User with read + write permissions
    test_user = AuthenticatedUser(
        user_id=str(uuid.uuid4()),
        role="GESTOR",
        permissions=["documents:read", "documents:write"],
        jti="classif-test-jti",
    )
    app.dependency_overrides[get_current_user] = lambda: test_user

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.mark.asyncio
async def test_classify_formato_unico_endpoint(classification_api_client: AsyncClient) -> None:
    fu_text = (
        "FORMATO ÚNICO DE HOJA DE VIDA\n"
        "PERSONA NATURAL\n"
        "DEPARTAMENTO ADMINISTRATIVO DE LA FUNCIÓN PÚBLICA\n\n"
        "1. DATOS PERSONALES\n"
        "PRIMER APELLIDO: VARGAS SEGUNDO APELLIDO: MORA NOMBRES: CAMILO ANDRES\n"
        "DOCUMENTO DE IDENTIFICACION: C.C. 1019283746\n"
        "LIBRETA MILITAR NUMERO: 1019283746\n\n"
        "2. FORMACION ACADEMICA\n"
        "UNIVERSIDAD DISTRITAL - INGENIERO ELECTRONICO\n\n"
        "3. EXPERIENCIA LABORAL\n"
        "EMPRESA O ENTIDAD: SECRETARIA DE EDUCACION\n"
        "CARGO O CONTRATO ACTUAL: INGENIERO DE SOPORTE\n"
        "FIRMA DEL SERVIDOR PUBLICO\n"
    )
    pdf_bytes = make_pdf(fu_text)

    # 1. Upload
    upload_resp = await classification_api_client.post(
        "/api/v1/documents",
        files={"file": ("fu_resume.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert upload_resp.status_code == 201
    doc_id = upload_resp.json()["document"]["id"]

    # 2. Classify
    classify_resp = await classification_api_client.post(f"/api/v1/documents/{doc_id}/classify")
    assert classify_resp.status_code == 200
    data = classify_resp.json()
    assert data["document_id"] == doc_id
    assert data["document_type"] == "FORMATO_UNICO"
    assert data["confidence"] >= 0.80
    assert data["is_definitive"] is True
    assert "FORMATO UNICO DE HOJA DE VIDA" in data["matched_indicators"]

    # 3. GET classification
    get_resp = await classification_api_client.get(f"/api/v1/documents/{doc_id}/classification")
    assert get_resp.status_code == 200
    get_data = get_resp.json()
    assert get_data["document_type"] == "FORMATO_UNICO"
    assert get_data["confidence"] == data["confidence"]

    # 4. Verify document detail has updated type
    detail_resp = await classification_api_client.get(f"/api/v1/documents/{doc_id}")
    assert detail_resp.status_code == 200
    assert detail_resp.json()["document"]["document_type"] == "FORMATO_UNICO"


@pytest.mark.asyncio
async def test_classify_ats_endpoint(classification_api_client: AsyncClient) -> None:
    ats_text = (
        "SEBASTIAN CASTILLO\n"
        "sebastian.castillo@cloudmail.com | +57 320 555 1234 | Medellin, Colombia\n"
        "linkedin.com/in/scastillo | github.com/scastillo\n\n"
        "PERFIL PROFESIONAL\n"
        "Desarrollador backend especialista en microservicios, bases de datos relacionales y cloud computing.\n\n"
        "EXPERIENCIA LABORAL\n"
        "Backend Developer — MercadoLibre Colombia (2022 - Actualidad)\n"
        "- Desarrollo de APIs de alta concurrencia con Go y Python.\n\n"
        "EDUCACION\n"
        "Universidad de Antioquia — Ingenieria de Sistemas (2016 - 2021)\n\n"
        "HABILIDADES TECNICAS\n"
        "Python, Go, Docker, Kubernetes, AWS, PostgreSQL, Redis, Kafka\n"
    )
    pdf_bytes = make_pdf(ats_text)

    # 1. Upload
    upload_resp = await classification_api_client.post(
        "/api/v1/documents",
        files={"file": ("ats_resume.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert upload_resp.status_code == 201
    doc_id = upload_resp.json()["document"]["id"]

    # 2. Classify
    classify_resp = await classification_api_client.post(f"/api/v1/documents/{doc_id}/classify")
    assert classify_resp.status_code == 200
    data = classify_resp.json()
    assert data["document_id"] == doc_id
    assert data["document_type"] == "ATS"
    assert data["confidence"] >= 0.60
    assert data["is_definitive"] is True

    # 3. Verify document detail reflects ATS
    detail_resp = await classification_api_client.get(f"/api/v1/documents/{doc_id}")
    assert detail_resp.status_code == 200
    assert detail_resp.json()["document"]["document_type"] == "ATS"


@pytest.mark.asyncio
async def test_classify_unknown_document_endpoint(classification_api_client: AsyncClient) -> None:
    invoice_text = (
        "FACTURA DE VENTA N° 849204\n"
        "FERRETERIA LA COLOMBIANA SAS\n"
        "NIT: 800.234.567-8\n"
        "SUBTOTAL: $450.000 COP\n"
        "IVA: $85.500 COP\n"
        "TOTAL A PAGAR: $535.500 COP\n"
        "PAGO RECIBIDO EN EFECTIVO. GRACIAS POR SU COMPRA.\n"
    )
    pdf_bytes = make_pdf(invoice_text)

    # 1. Upload
    upload_resp = await classification_api_client.post(
        "/api/v1/documents",
        files={"file": ("invoice.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert upload_resp.status_code == 201
    doc_id = upload_resp.json()["document"]["id"]

    # 2. Classify
    classify_resp = await classification_api_client.post(f"/api/v1/documents/{doc_id}/classify")
    assert classify_resp.status_code == 200
    data = classify_resp.json()
    assert data["document_type"] == "UNKNOWN"
    assert data["is_definitive"] is False

    # 3. Verify job is marked REVIEW_REQUIRED
    job_resp = await classification_api_client.get(f"/api/v1/documents/{doc_id}/job")
    assert job_resp.status_code == 200
    assert job_resp.json()["status"] == "REVIEW_REQUIRED"


@pytest.mark.asyncio
async def test_classify_nonexistent_document_returns_404(classification_api_client: AsyncClient) -> None:
    fake_id = uuid.uuid4()
    resp = await classification_api_client.post(f"/api/v1/documents/{fake_id}/classify")
    assert resp.status_code == 404
