"""
API integration tests for ATS resume extraction endpoints:
- POST /api/v1/documents/{id}/extract-ats
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

ATS_API_TEST_TEXT = """
CAROLINA MARIN RESTREPO
Senior Cloud & DevOps Engineer
Email: carolina.marin@cloudnative.co | Tel: +57 301 555 7788
Medellín, Colombia
https://www.linkedin.com/in/carolinamarin | https://github.com/carolinamarin
C.C. 1037648902

PERFIL PROFESIONAL
Ingeniera de sistemas especializada en arquitecturas nativas de la nube, automatización de infraestructura y microservicios con más de 7 años de experiencia.

EXPERIENCIA LABORAL
CloudNative Technologies - Lead DevOps Engineer
Ene 2021 - Presente
- Implementación de pipelines de despliegue continuo con GitHub Actions y Kubernetes.
- Automatización de entornos en AWS con Terraform y Docker.

Globant Colombia - Cloud Engineer
03/2017 - 12/2020
- Migración de aplicaciones monolíticas a microservicios distribuidos.
- Administración de clústeres de bases de datos PostgreSQL y Redis.

EDUCACIÓN
Ingeniera de Sistemas
Universidad de Antioquia
Año: 2016

HABILIDADES TÉCNICAS
Python, Go, Docker, Kubernetes, AWS, Terraform, PostgreSQL, Redis, Linux, Git, CI/CD, Scrum

IDIOMAS
Español: Nativo
Inglés: Avanzado (C1)

CERTIFICACIONES
AWS Certified Solutions Architect - 2022
"""


def make_pdf(text: str) -> bytes:
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 72), text)
    pdf_bytes = doc.write()
    doc.close()
    return pdf_bytes


@pytest_asyncio.fixture
async def ats_api_client(test_db: AsyncSession, tmp_path):
    app = create_application()

    app.dependency_overrides[get_db_session] = lambda: test_db

    test_storage = LocalStorageProvider(base_path=tmp_path)
    app.dependency_overrides[get_storage] = lambda: test_storage

    app.dependency_overrides[get_ocr] = lambda: MockOCRProvider()

    test_user = AuthenticatedUser(
        user_id=str(uuid.uuid4()),
        role="GESTOR",
        permissions=["documents:read", "documents:write"],
        jti="ats-test-jti",
    )
    app.dependency_overrides[get_current_user] = lambda: test_user

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.mark.asyncio
async def test_extract_ats_endpoint(ats_api_client: AsyncClient) -> None:
    pdf_bytes = make_pdf(ATS_API_TEST_TEXT)

    # 1. Upload document
    upload_resp = await ats_api_client.post(
        "/api/v1/documents",
        files={"file": ("cv_carolina_marin.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert upload_resp.status_code == 201
    doc_id = upload_resp.json()["document"]["id"]

    # 2. Extract ATS
    extract_resp = await ats_api_client.post(f"/api/v1/documents/{doc_id}/extract-ats")
    assert extract_resp.status_code == 200
    data = extract_resp.json()

    assert data["document_id"] == doc_id
    assert data["person_id"] is not None
    assert data["person"]["first_name"] == "CAROLINA"
    assert data["person"]["first_surname"] == "MARIN"
    assert data["person"]["second_surname"] == "RESTREPO"
    assert data["person"]["middle_name"] is None
    assert data["person"]["identification_number"] == "1037648902"
    assert data["contact"]["email"] == "carolina.marin@cloudnative.co"
    assert "+57 301 555 7788" in str(data["contact"]["telephone"])
    assert data["contact"]["municipality"] == "Medellín"

    # Verify work experiences
    assert len(data["work_experiences"]) == 2
    assert "CloudNative Technologies" in data["work_experiences"][0]["company_name"]
    assert data["work_experiences"][0]["is_current"] is True

    # Verify educations
    assert len(data["educations"]) >= 1
    assert "Ingeniera de Sistemas" in data["educations"][0]["degree_title"]
    assert data["educations"][0]["completion_year"] == 2016

    # Verify languages
    assert len(data["languages"]) >= 1

    # 3. GET canonical resume
    get_resp = await ats_api_client.get(f"/api/v1/documents/{doc_id}/canonical-resume")
    assert get_resp.status_code == 200
    get_data = get_resp.json()
    assert get_data["document_id"] == doc_id
    assert get_data["person"]["first_name"] == "CAROLINA"
    assert get_data["person_id"] == data["person_id"]

    # 4. Check document detail has person_id linked
    doc_detail = await ats_api_client.get(f"/api/v1/documents/{doc_id}")
    assert doc_detail.status_code == 200
    assert doc_detail.json()["document"]["person_id"] == data["person_id"]


@pytest.mark.asyncio
async def test_extract_ats_nonexistent_returns_404(ats_api_client: AsyncClient) -> None:
    fake_id = uuid.uuid4()
    resp = await ats_api_client.post(f"/api/v1/documents/{fake_id}/extract-ats")
    assert resp.status_code == 404
