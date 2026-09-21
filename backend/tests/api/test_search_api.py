"""
API integration tests for Search and Candidate Dossier endpoints:
- GET  /api/v1/search/candidates
- GET  /api/v1/search/candidates/{id}
- GET  /api/v1/search/facets
- GET  /api/v1/search/filter-options
- POST /api/v1/search/candidates/{id}/classify-profession
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

SAMPLE_RESUME_TEXT = """
CAROLINA MARIN RESTREPO
Senior Cloud & DevOps Engineer
Email: carolina.marin@cloudnative.co | Tel: +57 301 555 7788
Medellín, Colombia
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
async def search_api_client(test_db: AsyncSession, tmp_path):
    app = create_application()

    app.dependency_overrides[get_db_session] = lambda: test_db

    test_storage = LocalStorageProvider(base_path=tmp_path)
    app.dependency_overrides[get_storage] = lambda: test_storage

    app.dependency_overrides[get_ocr] = lambda: MockOCRProvider()

    test_user = AuthenticatedUser(
        user_id=str(uuid.uuid4()),
        role="DIRECTOR",
        permissions=["documents:read", "documents:write"],
        jti="search-test-jti",
    )
    app.dependency_overrides[get_current_user] = lambda: test_user

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.mark.asyncio
async def test_filter_options_endpoint(search_api_client: AsyncClient) -> None:
    resp = await search_api_client.get("/api/v1/search/filter-options")
    assert resp.status_code == 200
    data = resp.json()
    assert "categories" in data
    assert len(data["categories"]) > 0
    assert "departments" in data
    assert "Bogotá D.C." in data["departments"]
    assert "academic_levels" in data
    assert "UNDERGRADUATE" in data["academic_levels"]


@pytest.mark.asyncio
async def test_facets_endpoint(search_api_client: AsyncClient) -> None:
    resp = await search_api_client.get("/api/v1/search/facets")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_candidates" in data
    assert "by_category" in data
    assert "by_profession" in data
    assert "by_academic_level" in data
    assert "by_department" in data


@pytest.mark.asyncio
async def test_full_search_and_dossier_workflow(search_api_client: AsyncClient) -> None:
    # 1. Upload and extract a candidate
    pdf_bytes = make_pdf(SAMPLE_RESUME_TEXT)
    upload_resp = await search_api_client.post(
        "/api/v1/documents",
        files={"file": ("cv_carolina_marin.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert upload_resp.status_code == 201
    doc_id = upload_resp.json()["document"]["id"]

    extract_resp = await search_api_client.post(f"/api/v1/documents/{doc_id}/extract-ats")
    assert extract_resp.status_code == 200
    person_id = extract_resp.json()["person_id"]
    assert person_id is not None

    # 2. General full-text search `q=Carolina`
    search_q = await search_api_client.get("/api/v1/search/candidates?q=Carolina")
    assert search_q.status_code == 200
    data_q = search_q.json()
    assert data_q["total"] >= 1
    assert any(c["id"] == person_id for c in data_q["items"])
    assert data_q["page"] == 1
    assert data_q["total_pages"] >= 1

    # 3. Filter by identification_number
    search_id = await search_api_client.get("/api/v1/search/candidates?identification_number=1037648902")
    assert search_id.status_code == 200
    assert search_id.json()["total"] >= 1

    # 4. Filter by company
    search_comp = await search_api_client.get("/api/v1/search/candidates?company=CloudNative")
    assert search_comp.status_code == 200
    assert search_comp.json()["total"] >= 1

    # 5. Filter by municipality
    search_mun = await search_api_client.get("/api/v1/search/candidates?municipality=Medellín")
    assert search_mun.status_code == 200
    assert search_mun.json()["total"] >= 1

    # 6. Sorting and pagination
    search_sort = await search_api_client.get("/api/v1/search/candidates?sort_by=name&sort_order=asc&page=1&page_size=5")
    assert search_sort.status_code == 200
    sort_data = search_sort.json()
    assert len(sort_data["items"]) <= 5

    # 7. Get full candidate dossier
    detail_resp = await search_api_client.get(f"/api/v1/search/candidates/{person_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["id"] == person_id
    assert "CAROLINA" in detail["full_name"]
    assert detail["contact"]["email"] == "carolina.marin@cloudnative.co"
    assert len(detail["educations"]) >= 1
    assert len(detail["work_experiences"]) == 2
    assert len(detail["languages"]) >= 1
    assert len(detail["skills"]) >= 5
    assert len(detail["documents"]) >= 1

    # 8. Auto-classify candidate profession
    classify_resp = await search_api_client.post(f"/api/v1/search/candidates/{person_id}/classify-profession")
    assert classify_resp.status_code == 200
    class_data = classify_resp.json()
    assert class_data["person_id"] == person_id
    assert class_data["category_name"] == "Ingeniería y Tecnología"
    assert "Sistemas" in class_data["profession_name"]


@pytest.mark.asyncio
async def test_search_candidate_not_found(search_api_client: AsyncClient) -> None:
    fake_id = uuid.uuid4()
    resp = await search_api_client.get(f"/api/v1/search/candidates/{fake_id}")
    assert resp.status_code == 404

    resp_class = await search_api_client.post(f"/api/v1/search/candidates/{fake_id}/classify-profession")
    assert resp_class.status_code == 404
