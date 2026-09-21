"""
API integration tests for Dashboard and Institutional Analytics endpoints:
- GET /api/v1/dashboard/overview
- GET /api/v1/dashboard/kpis
- GET /api/v1/dashboard/distributions
- GET /api/v1/dashboard/pending-reviews
- GET /api/v1/dashboard/recent-activity
- Security: RBAC 401 / 403 enforcement
"""

from datetime import datetime, timezone
import uuid
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.constants import JobStatus
from app.infrastructure.database.models.document_models import (
    Document,
    ProcessingJob,
)
from app.infrastructure.database.models.person_models import (
    ContactInformation,
    Person,
    Profession,
    ProfessionalCategory,
)
from app.infrastructure.database.models.resume_models import (
    Education,
    ExperienceSummary,
)
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


@pytest_asyncio.fixture
async def dashboard_client(test_db: AsyncSession, tmp_path):
    app = create_application()

    app.dependency_overrides[get_db_session] = lambda: test_db

    test_storage = LocalStorageProvider(base_path=tmp_path)
    app.dependency_overrides[get_storage] = lambda: test_storage
    app.dependency_overrides[get_ocr] = lambda: MockOCRProvider()

    test_user = AuthenticatedUser(
        user_id=str(uuid.uuid4()),
        role="DIRECTOR",
        permissions=["documents:read", "documents:write"],
        jti="dashboard-test-jti",
    )
    app.dependency_overrides[get_current_user] = lambda: test_user

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


@pytest_asyncio.fixture
async def unauthorized_dashboard_client(test_db: AsyncSession):
    app = create_application()
    app.dependency_overrides[get_db_session] = lambda: test_db

    # User with no read permissions
    low_priv_user = AuthenticatedUser(
        user_id=str(uuid.uuid4()),
        role="CANDIDATE",
        permissions=[],
        jti="unauthorized-jti",
    )
    app.dependency_overrides[get_current_user] = lambda: low_priv_user

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.mark.asyncio
async def test_dashboard_overview_empty_db(dashboard_client: AsyncClient) -> None:
    resp = await dashboard_client.get("/api/v1/dashboard/overview")
    assert resp.status_code == 200
    data = resp.json()

    assert "kpis" in data
    assert "distributions" in data
    assert "pending_reviews" in data
    assert "recent_activity" in data

    # Empty DB default KPIs
    kpis = data["kpis"]
    assert kpis["total_documents"] == 0
    assert kpis["total_persons"] == 0
    assert kpis["extraction_success_rate"] == 100.0


@pytest.mark.asyncio
async def test_dashboard_kpis_endpoint(dashboard_client: AsyncClient) -> None:
    resp = await dashboard_client.get("/api/v1/dashboard/kpis")
    assert resp.status_code == 200
    data = resp.json()

    assert "total_documents" in data
    assert "total_persons" in data
    assert "total_professionals" in data
    assert "processed_documents" in data
    assert "documents_requiring_review" in data
    assert "extraction_success_rate" in data


@pytest.mark.asyncio
async def test_dashboard_distributions_endpoint(dashboard_client: AsyncClient) -> None:
    resp = await dashboard_client.get("/api/v1/dashboard/distributions")
    assert resp.status_code == 200
    data = resp.json()

    assert "by_format" in data
    assert "by_category" in data
    assert "top_professions" in data
    assert "by_academic_level" in data
    assert "by_experience" in data
    assert "by_geography" in data


@pytest.mark.asyncio
async def test_dashboard_pending_reviews_endpoint(dashboard_client: AsyncClient) -> None:
    resp = await dashboard_client.get("/api/v1/dashboard/pending-reviews?limit=5")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_dashboard_recent_activity_endpoint(dashboard_client: AsyncClient) -> None:
    resp = await dashboard_client.get("/api/v1/dashboard/recent-activity?limit=5")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_dashboard_forbidden_without_permission(
    unauthorized_dashboard_client: AsyncClient,
) -> None:
    resp = await unauthorized_dashboard_client.get("/api/v1/dashboard/overview")
    assert resp.status_code == 403

    resp_kpi = await unauthorized_dashboard_client.get("/api/v1/dashboard/kpis")
    assert resp_kpi.status_code == 403


@pytest.mark.asyncio
async def test_dashboard_with_populated_database(
    dashboard_client: AsyncClient,
    test_db: AsyncSession,
) -> None:
    """Test dashboard metrics after seeding data into test DB."""
    # 1. Create category and profession
    cat = ProfessionalCategory(
        id=uuid.uuid4(),
        name="Ingeniería y Tecnología",
        description="Área tecnológica",
    )
    test_db.add(cat)
    await test_db.flush()

    prof = Profession(
        id=uuid.uuid4(),
        category_id=cat.id,
        name="Ingeniero de Software",
    )
    test_db.add(prof)
    await test_db.flush()

    # 2. Create person with education, experience summary and contact info
    person = Person(
        id=uuid.uuid4(),
        first_name="Carlos",
        first_surname="Restrepo",
        identification_type="CC",
        identification_number="1020304050",
        primary_category_id=cat.id,
        primary_profession_id=prof.id,
    )
    test_db.add(person)
    await test_db.flush()

    contact = ContactInformation(
        id=uuid.uuid4(),
        person_id=person.id,
        email="carlos@example.com",
        department="Antioquia",
        municipality="Medellín",
    )
    test_db.add(contact)

    edu = Education(
        id=uuid.uuid4(),
        person_id=person.id,
        level="UNDERGRADUATE",
        degree_title="Ingeniería de Sistemas",
        institution="Universidad de Antioquia",
    )
    test_db.add(edu)

    exp_summary = ExperienceSummary(
        id=uuid.uuid4(),
        person_id=person.id,
        total_years=4,
        total_months=48,
    )
    test_db.add(exp_summary)

    # 3. Create document and processing job requiring review
    doc = Document(
        id=uuid.uuid4(),
        person_id=person.id,
        uploaded_by=uuid.uuid4(),
        original_filename="carlos_hv.pdf",
        storage_key="documents/carlos_hv.pdf",
        checksum_sha256="1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
        file_size_bytes=524288,
        mime_type="application/pdf",
        document_type="FORMATO_UNICO",
        page_count=3,
    )
    test_db.add(doc)
    await test_db.flush()

    job = ProcessingJob(
        id=uuid.uuid4(),
        document_id=doc.id,
        status=JobStatus.REVIEW_REQUIRED.value,
        current_step="review_required",
        error_message="Campos con baja confianza detectados",
    )
    test_db.add(job)
    await test_db.commit()

    # Query overview endpoint
    resp = await dashboard_client.get("/api/v1/dashboard/overview")
    assert resp.status_code == 200
    data = resp.json()

    # Validate KPIs
    kpis = data["kpis"]
    assert kpis["total_documents"] >= 1
    assert kpis["total_persons"] >= 1
    assert kpis["total_professionals"] >= 1
    assert kpis["documents_requiring_review"] >= 1

    # Validate Distributions
    dist = data["distributions"]
    assert any(item["label"] == "FORMATO_UNICO" for item in dist["by_format"])
    assert any(item["label"] == "Ingeniería y Tecnología" for item in dist["by_category"])
    assert any(item["label"] == "Ingeniero de Software" for item in dist["top_professions"])
    assert any(item["label"] == "UNDERGRADUATE" for item in dist["by_academic_level"])
    assert dist["by_experience"]["3_to_5_years"] >= 1
    assert any(item["label"] == "Antioquia" for item in dist["by_geography"])

    # Validate Pending Reviews
    pending = data["pending_reviews"]
    assert len(pending) >= 1
    assert pending[0]["filename"] == "carlos_hv.pdf"
    assert pending[0]["current_step"] == "review_required"

    # Validate Recent Activity
    activity = data["recent_activity"]
    assert len(activity) >= 1
    assert activity[0]["filename"] == "carlos_hv.pdf"
    assert activity[0]["candidate_name"] == "Carlos Restrepo"
    assert activity[0]["status"] == JobStatus.REVIEW_REQUIRED.value
