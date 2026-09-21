"""
API integration tests for Formato Único extraction endpoints:
- POST /api/v1/documents/{id}/extract-formato-unico
- GET  /api/v1/documents/{id}/canonical-resume
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

FU_TEST_TEXT = (
    "FORMATO ÚNICO DE HOJA DE VIDA\n"
    "PERSONA NATURAL\n"
    "REPÚBLICA DE COLOMBIA\n"
    "DEPARTAMENTO ADMINISTRATIVO DE LA FUNCIÓN PÚBLICA\n\n"
    "1. DATOS PERSONALES\n"
    "PRIMER APELLIDO: HERNANDEZ\n"
    "SEGUNDO APELLIDO: SILVA\n"
    "NOMBRES: JORGE EDUARDO\n"
    "DOCUMENTO DE IDENTIFICACIÓN: C.C. 79482103\n"
    "SEXO: MASCULINO NACIONALIDAD: COLOMBIANA\n"
    "FECHA DE NACIMIENTO: 10/08/1982\n"
    "LIBRETA MILITAR: NÚMERO 79482103 DISTRITO: 15 CLASE: PRIMERA\n"
    "DIRECCIÓN: CARRERA 7 # 32-16\n"
    "MUNICIPIO: BOGOTA\n"
    "CORREO ELECTRÓNICO: jorge.hernandez@gobierno.gov.co\n\n"
    "2. FORMACIÓN ACADÉMICA\n"
    "EDUCACIÓN BÁSICA Y MEDIA: TÍTULO OBTENIDO: BACHILLER ACADÉMICO\n"
    "EDUCACIÓN SUPERIOR: MODALIDAD: UNIVERSITARIA GRADUADO: SÍ\n"
    "NOMBRE DE LA INSTITUCIÓN: UNIVERSIDAD NACIONAL DE COLOMBIA\n"
    "TÍTULO: INGENIERO CIVIL\n"
    "FECHA DE GRADO: AÑO: 2005 MES: 11\n"
    "TARJETA PROFESIONAL: 11223344\n\n"
    "IDIOMAS: INGLÉS HABLA: BIEN LEE: BIEN ESCRIBE: BIEN\n\n"
    "3. EXPERIENCIA LABORAL\n"
    "EMPRESA O ENTIDAD: INSTITUTO DE DESARROLLO URBANO IDU\n"
    "PÚBLICA CARGO O CONTRATO ACTUAL: DIRECTOR TECNICO\n"
    "FECHA DE INGRESO: 01/01/2015 FECHA DE RETIRO: 30/06/2021\n\n"
    "4. TIEMPO TOTAL DE EXPERIENCIA\n"
    "SERVIDOR PÚBLICO: 6 AÑOS, 6 MESES\n"
    "TOTAL TIEMPO DE EXPERIENCIA: 6 AÑOS, 6 MESES\n"
)


def make_pdf(text: str) -> bytes:
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 72), text)
    pdf_bytes = doc.write()
    doc.close()
    return pdf_bytes


@pytest_asyncio.fixture
async def fu_api_client(test_db: AsyncSession, tmp_path):
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
        jti="fu-test-jti",
    )
    app.dependency_overrides[get_current_user] = lambda: test_user

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.mark.asyncio
async def test_extract_formato_unico_endpoint(fu_api_client: AsyncClient) -> None:
    pdf_bytes = make_pdf(FU_TEST_TEXT)

    # 1. Upload document
    upload_resp = await fu_api_client.post(
        "/api/v1/documents",
        files={"file": ("dafp_hernandez.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert upload_resp.status_code == 201
    doc_id = upload_resp.json()["document"]["id"]

    # 2. Extract Formato Único
    extract_resp = await fu_api_client.post(f"/api/v1/documents/{doc_id}/extract-formato-unico")
    assert extract_resp.status_code == 200
    data = extract_resp.json()

    assert data["document_id"] == doc_id
    assert data["person_id"] is not None
    assert data["person"]["first_surname"] == "HERNANDEZ"
    assert data["person"]["first_name"] == "JORGE"
    assert data["person"]["identification_number"] == "79482103"
    assert data["person"]["military_card_number"] == "79482103"
    assert data["contact"]["email"] == "jorge.hernandez@gobierno.gov.co"

    # Verify educations
    assert len(data["educations"]) >= 1
    assert any("INGENIERO CIVIL" in (e["degree_title"] or "").upper() for e in data["educations"])

    # Verify experiences
    assert len(data["work_experiences"]) == 1
    assert "IDU" in data["work_experiences"][0]["company_name"].upper()
    assert data["work_experiences"][0]["sector"] == "PUBLIC"

    # Verify summary
    assert data["experience_summary"] is not None
    assert data["experience_summary"]["public_years"] == 6

    # 3. Query GET canonical resume
    get_resp = await fu_api_client.get(f"/api/v1/documents/{doc_id}/canonical-resume")
    assert get_resp.status_code == 200
    get_data = get_resp.json()
    assert get_data["document_id"] == doc_id
    assert get_data["person"]["first_surname"] == "HERNANDEZ"
    assert get_data["person_id"] == data["person_id"]

    # 4. Check document detail has person_id linked
    doc_detail = await fu_api_client.get(f"/api/v1/documents/{doc_id}")
    assert doc_detail.status_code == 200
    assert doc_detail.json()["document"]["person_id"] == data["person_id"]


@pytest.mark.asyncio
async def test_extract_formato_unico_nonexistent_returns_404(fu_api_client: AsyncClient) -> None:
    fake_id = uuid.uuid4()
    resp = await fu_api_client.post(f"/api/v1/documents/{fake_id}/extract-formato-unico")
    assert resp.status_code == 404
