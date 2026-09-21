"""
Unit tests for DashboardRepository.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
import uuid
import pytest

from app.config.constants import JobStatus
from app.infrastructure.database.models.document_models import (
    Document,
    ProcessingJob,
)
from app.infrastructure.database.models.person_models import (
    Person,
    Profession,
    ProfessionalCategory,
)
from app.infrastructure.database.repositories.dashboard_repository import (
    DashboardRepository,
)


@pytest.mark.asyncio
async def test_get_kpis_empty_db():
    db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar.return_value = 0
    db.execute.return_value = mock_res

    repo = DashboardRepository(db)
    kpis = await repo.get_kpis()

    assert kpis["total_documents"] == 0
    assert kpis["total_persons"] == 0
    assert kpis["total_professionals"] == 0
    assert kpis["processed_documents"] == 0
    assert kpis["documents_requiring_review"] == 0
    assert kpis["extraction_success_rate"] == 100.0


@pytest.mark.asyncio
async def test_get_kpis_with_data():
    db = AsyncMock()
    res1 = MagicMock()
    res1.scalar.return_value = 10  # total_docs
    res2 = MagicMock()
    res2.scalar.return_value = 8   # total_persons
    res3 = MagicMock()
    res3.scalar.return_value = 6   # total_professionals
    res4 = MagicMock()
    res4.scalar.return_value = 7   # processed_docs
    res5 = MagicMock()
    res5.scalar.return_value = 2   # requiring_review

    db.execute.side_effect = [res1, res2, res3, res4, res5]

    repo = DashboardRepository(db)
    kpis = await repo.get_kpis()

    assert kpis["total_documents"] == 10
    assert kpis["total_persons"] == 8
    assert kpis["total_professionals"] == 6
    assert kpis["processed_documents"] == 7
    assert kpis["documents_requiring_review"] == 2
    assert kpis["extraction_success_rate"] == 70.0


@pytest.mark.asyncio
async def test_get_format_distribution():
    db = AsyncMock()
    mock_res = MagicMock()
    mock_res.all.return_value = [
        ("FORMATO_UNICO", 7),
        ("ATS_RESUME", 3),
    ]
    db.execute.return_value = mock_res

    repo = DashboardRepository(db)
    dist = await repo.get_format_distribution()

    assert len(dist) == 2
    assert dist[0]["label"] == "FORMATO_UNICO"
    assert dist[0]["count"] == 7
    assert dist[0]["percentage"] == 70.0
    assert dist[1]["label"] == "ATS_RESUME"
    assert dist[1]["count"] == 3
    assert dist[1]["percentage"] == 30.0


@pytest.mark.asyncio
async def test_get_category_distribution():
    db = AsyncMock()
    mock_res = MagicMock()
    mock_res.all.return_value = [
        ("Ingeniería y Tecnología", 15),
        ("Ciencias de la Salud", 5),
    ]
    db.execute.return_value = mock_res

    repo = DashboardRepository(db)
    dist = await repo.get_category_distribution()

    assert len(dist) == 2
    assert dist[0]["label"] == "Ingeniería y Tecnología"
    assert dist[0]["count"] == 15
    assert dist[0]["percentage"] == 75.0
    assert dist[1]["label"] == "Ciencias de la Salud"
    assert dist[1]["count"] == 5
    assert dist[1]["percentage"] == 25.0


@pytest.mark.asyncio
async def test_get_top_professions():
    db = AsyncMock()
    mock_res = MagicMock()
    mock_res.all.return_value = [
        ("Ingeniero de Sistemas", 8),
        ("Médico General", 2),
    ]
    db.execute.return_value = mock_res

    repo = DashboardRepository(db)
    dist = await repo.get_top_professions(limit=5)

    assert len(dist) == 2
    assert dist[0]["label"] == "Ingeniero de Sistemas"
    assert dist[0]["count"] == 8
    assert dist[0]["percentage"] == 80.0
    assert dist[1]["label"] == "Médico General"
    assert dist[1]["count"] == 2
    assert dist[1]["percentage"] == 20.0


@pytest.mark.asyncio
async def test_get_academic_level_distribution():
    db = AsyncMock()
    mock_res = MagicMock()
    mock_res.all.return_value = [
        ("UNDERGRADUATE", 12),
        ("MASTER", 4),
    ]
    db.execute.return_value = mock_res

    repo = DashboardRepository(db)
    dist = await repo.get_academic_level_distribution()

    assert len(dist) == 2
    assert dist[0]["label"] == "UNDERGRADUATE"
    assert dist[0]["count"] == 12
    assert dist[0]["percentage"] == 75.0


@pytest.mark.asyncio
async def test_get_experience_distribution():
    db = AsyncMock()
    mock_res = MagicMock()
    mock_res.one_or_none.return_value = (5, 8, 4, 3)
    db.execute.return_value = mock_res

    repo = DashboardRepository(db)
    exp = await repo.get_experience_distribution()

    assert exp["0_to_2_years"] == 5
    assert exp["3_to_5_years"] == 8
    assert exp["6_to_10_years"] == 4
    assert exp["more_than_10_years"] == 3


@pytest.mark.asyncio
async def test_get_geographic_distribution():
    db = AsyncMock()
    mock_res = MagicMock()
    mock_res.all.return_value = [
        ("Bogotá D.C.", 10),
        ("Antioquia", 6),
    ]
    db.execute.return_value = mock_res

    repo = DashboardRepository(db)
    geo = await repo.get_geographic_distribution(limit=5)

    assert len(geo) == 2
    assert geo[0]["label"] == "Bogotá D.C."
    assert geo[0]["count"] == 10
    assert geo[0]["percentage"] == 62.5
    assert geo[1]["label"] == "Antioquia"
    assert geo[1]["count"] == 6
    assert geo[1]["percentage"] == 37.5


@pytest.mark.asyncio
async def test_get_documents_requiring_review():
    db = AsyncMock()
    now = datetime.now(timezone.utc)
    doc_id = uuid.uuid4()
    job_id = uuid.uuid4()

    mock_doc = MagicMock()
    mock_doc.id = doc_id
    mock_doc.original_filename = "cv_pedro.pdf"
    mock_doc.document_type = "ATS_RESUME"
    mock_doc.created_at = now

    mock_job = MagicMock()
    mock_job.id = job_id
    mock_job.current_step = "review_required"
    mock_job.error_message = "Confianza baja en campos requeridos"

    mock_res = MagicMock()
    # Provide duplicate doc to verify deduplication
    mock_res.all.return_value = [(mock_doc, mock_job), (mock_doc, mock_job)]
    db.execute.return_value = mock_res

    repo = DashboardRepository(db)
    items = await repo.get_documents_requiring_review(limit=5)

    assert len(items) == 1
    assert items[0]["document_id"] == doc_id
    assert items[0]["filename"] == "cv_pedro.pdf"
    assert items[0]["document_type"] == "ATS_RESUME"
    assert items[0]["job_id"] == job_id
    assert items[0]["current_step"] == "review_required"
    assert items[0]["error_message"] == "Confianza baja en campos requeridos"


@pytest.mark.asyncio
async def test_get_recent_activity():
    db = AsyncMock()
    now = datetime.now(timezone.utc)
    doc_id = uuid.uuid4()
    person_id = uuid.uuid4()

    mock_person = MagicMock()
    mock_person.first_name = "Laura"
    mock_person.first_surname = "Gomez"

    mock_job = MagicMock()
    mock_job.status = JobStatus.COMPLETED.value
    mock_job.created_at = now

    mock_doc = MagicMock()
    mock_doc.id = doc_id
    mock_doc.original_filename = "laura_cv.pdf"
    mock_doc.document_type = "FORMATO_UNICO"
    mock_doc.person = mock_person
    mock_doc.person_id = person_id
    mock_doc.processing_jobs = [mock_job]
    mock_doc.file_size_bytes = 1048576
    mock_doc.created_at = now

    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [mock_doc]
    db.execute.return_value = mock_res

    repo = DashboardRepository(db)
    items = await repo.get_recent_activity(limit=5)

    assert len(items) == 1
    assert items[0]["document_id"] == doc_id
    assert items[0]["filename"] == "laura_cv.pdf"
    assert items[0]["document_type"] == "FORMATO_UNICO"
    assert items[0]["candidate_name"] == "Laura Gomez"
    assert items[0]["person_id"] == person_id
    assert items[0]["status"] == JobStatus.COMPLETED.value
    assert items[0]["file_size_bytes"] == 1048576
