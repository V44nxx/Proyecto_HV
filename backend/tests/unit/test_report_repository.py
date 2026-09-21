"""
Unit tests for ReportRepository.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
import uuid
import pytest

from app.domain.value_objects.report_types import ReportType
from app.infrastructure.database.models.document_models import Document, ProcessingJob
from app.infrastructure.database.models.person_models import (
    ContactInformation,
    Person,
    Profession,
    ProfessionalCategory,
)
from app.infrastructure.database.models.resume_models import (
    Education,
    ExperienceSummary,
    WorkExperience,
)
from app.infrastructure.database.repositories.report_repository import ReportRepository


@pytest.mark.asyncio
async def test_get_inventory_dataset():
    db = AsyncMock()
    now = datetime.now(timezone.utc)

    mock_person = MagicMock()
    mock_person.first_name = "Carlos"
    mock_person.first_surname = "Mendoza"
    mock_person.identification_number = "10203040"

    mock_job = MagicMock()
    mock_job.status = "COMPLETED"
    mock_job.created_at = now

    mock_doc = MagicMock()
    mock_doc.original_filename = "carlos_hv.pdf"
    mock_doc.document_type = "FORMATO_UNICO"
    mock_doc.file_size_bytes = 204800
    mock_doc.page_count = 2
    mock_doc.created_at = now
    mock_doc.person = mock_person
    mock_doc.processing_jobs = [mock_job]

    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [mock_doc]
    db.execute.return_value = mock_res

    repo = ReportRepository(db)
    dataset = await repo.get_inventory_dataset(
        filters={"status": "COMPLETED"},
        generated_by="admin@test.com",
    )

    assert dataset.report_type == ReportType.INVENTORY
    assert dataset.total_records == 1
    assert len(dataset.rows) == 1
    assert dataset.rows[0]["filename"] == "carlos_hv.pdf"
    assert dataset.rows[0]["candidate_name"] == "Carlos Mendoza"
    assert dataset.rows[0]["status"] == "COMPLETED"
    assert dataset.rows[0]["size_kb"] == 200.0


@pytest.mark.asyncio
async def test_get_classification_dataset():
    db = AsyncMock()
    cat = ProfessionalCategory(id=uuid.uuid4(), name="Ingeniería y Tecnología")
    prof = Profession(id=uuid.uuid4(), category_id=cat.id, name="Ingeniero de Sistemas")
    exp = ExperienceSummary(id=uuid.uuid4(), person_id=uuid.uuid4(), total_years=5)
    edu = Education(id=uuid.uuid4(), person_id=uuid.uuid4(), level="UNDERGRADUATE")
    contact = ContactInformation(id=uuid.uuid4(), person_id=uuid.uuid4(), department="Antioquia", municipality="Medellín")

    person = Person(
        id=uuid.uuid4(),
        first_name="Diana",
        first_surname="Vargas",
        identification_type="CC",
        identification_number="987654",
    )
    person.primary_category = cat
    person.primary_profession = prof
    person.experience_summary = exp
    person.educations = [edu]
    person.contact_information = contact

    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [person]
    db.execute.return_value = mock_res

    repo = ReportRepository(db)
    dataset = await repo.get_classification_dataset(
        filters={"min_years_experience": 3},
        generated_by="director@test.com",
    )

    assert dataset.report_type == ReportType.PROFESSIONAL_CLASSIFICATION
    assert dataset.total_records == 1
    assert dataset.rows[0]["candidate_name"] == "Diana Vargas"
    assert dataset.rows[0]["profession"] == "Ingeniero de Sistemas"
    assert dataset.rows[0]["category"] == "Ingeniería y Tecnología"
    assert dataset.rows[0]["academic_level"] == "UNDERGRADUATE"
    assert dataset.rows[0]["experience_years"] == 5


@pytest.mark.asyncio
async def test_get_academic_dataset():
    db = AsyncMock()
    person = Person(
        id=uuid.uuid4(),
        first_name="Esteban",
        first_surname="Castro",
        identification_number="11223344",
    )
    edu = Education(
        id=uuid.uuid4(),
        person_id=person.id,
        level="MASTER",
        degree_title="Maestría en Ciberseguridad",
        institution="Universidad de los Andes",
        graduation_status="GRADUATED",
        professional_card_no="TP-9988",
    )
    edu.person = person

    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [edu]
    db.execute.return_value = mock_res

    repo = ReportRepository(db)
    dataset = await repo.get_academic_dataset(
        filters={"academic_level": "MASTER"},
        generated_by="consultor@test.com",
    )

    assert dataset.report_type == ReportType.ACADEMIC
    assert dataset.total_records == 1
    assert dataset.rows[0]["candidate_name"] == "Esteban Castro"
    assert dataset.rows[0]["level"] == "MASTER"
    assert dataset.rows[0]["degree_title"] == "Maestría en Ciberseguridad"
    assert dataset.rows[0]["institution"] == "Universidad de los Andes"


@pytest.mark.asyncio
async def test_get_experience_dataset():
    db = AsyncMock()
    prof = Profession(id=uuid.uuid4(), name="Desarrollador Full-Stack")
    exp = ExperienceSummary(
        id=uuid.uuid4(),
        person_id=uuid.uuid4(),
        total_years=8,
        public_years=2,
        private_years=6,
        independent_years=0,
    )
    work = WorkExperience(
        id=uuid.uuid4(),
        person_id=uuid.uuid4(),
        company_name="Tech Solutions SAS",
        position="Líder Técnico",
        start_date=datetime(2021, 1, 1),
    )

    person = Person(
        id=uuid.uuid4(),
        first_name="Gabriel",
        first_surname="Reyes",
        identification_number="55667788",
    )
    person.primary_profession = prof
    person.experience_summary = exp
    person.work_experiences = [work]

    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [person]
    db.execute.return_value = mock_res

    repo = ReportRepository(db)
    dataset = await repo.get_experience_dataset(
        filters={"company": "Tech Solutions"},
        generated_by="gestor@test.com",
    )

    assert dataset.report_type == ReportType.EXPERIENCE
    assert dataset.total_records == 1
    assert dataset.rows[0]["candidate_name"] == "Gabriel Reyes"
    assert dataset.rows[0]["total_years"] == 8
    assert dataset.rows[0]["private_years"] == 6
    assert dataset.rows[0]["last_position"] == "Líder Técnico"
    assert dataset.rows[0]["last_company"] == "Tech Solutions SAS"


@pytest.mark.asyncio
async def test_get_geographic_dataset():
    db = AsyncMock()
    contact = ContactInformation(
        id=uuid.uuid4(),
        person_id=uuid.uuid4(),
        department="Cundinamarca",
        municipality="Bogotá D.C.",
        email="gabriel@example.co",
        mobile_phone="3001234567",
    )
    prof = Profession(id=uuid.uuid4(), name="Economista")
    person = Person(
        id=uuid.uuid4(),
        first_name="Helena",
        first_surname="Pardo",
        identification_number="33445566",
    )
    person.contact_information = contact
    person.primary_profession = prof

    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [person]
    db.execute.return_value = mock_res

    repo = ReportRepository(db)
    dataset = await repo.get_geographic_dataset(
        filters={"department": "Cundinamarca"},
        generated_by="admin@test.com",
    )

    assert dataset.report_type == ReportType.GEOGRAPHIC
    assert dataset.total_records == 1
    assert dataset.rows[0]["candidate_name"] == "Helena Pardo"
    assert dataset.rows[0]["department"] == "Cundinamarca"
    assert dataset.rows[0]["municipality"] == "Bogotá D.C."
    assert dataset.rows[0]["email"] == "gabriel@example.co"
    assert dataset.rows[0]["profession"] == "Economista"


@pytest.mark.asyncio
async def test_get_custom_filtered_dataset():
    db = AsyncMock()
    cat = ProfessionalCategory(id=uuid.uuid4(), name="Salud")
    prof = Profession(id=uuid.uuid4(), category_id=cat.id, name="Médico Cirujano")
    exp = ExperienceSummary(id=uuid.uuid4(), person_id=uuid.uuid4(), total_years=10)
    contact = ContactInformation(id=uuid.uuid4(), person_id=uuid.uuid4(), department="Valle del Cauca", municipality="Cali")
    edu = Education(id=uuid.uuid4(), person_id=uuid.uuid4(), level="DOCTORATE")

    person = Person(
        id=uuid.uuid4(),
        first_name="Ignacio",
        first_surname="Lozano",
        identification_number="77889900",
    )
    person.primary_category = cat
    person.primary_profession = prof
    person.experience_summary = exp
    person.contact_information = contact
    person.educations = [edu]

    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [person]
    db.execute.return_value = mock_res

    repo = ReportRepository(db)
    dataset = await repo.get_custom_filtered_dataset(
        filters={"identification_number": "77889900"},
        generated_by="director@test.com",
    )

    assert dataset.report_type == ReportType.CUSTOM_FILTERED
    assert dataset.total_records == 1
    assert dataset.rows[0]["candidate_name"] == "Ignacio Lozano"
    assert dataset.rows[0]["category"] == "Salud"
    assert dataset.rows[0]["profession"] == "Médico Cirujano"
    assert dataset.rows[0]["academic_level"] == "DOCTORATE"


@pytest.mark.asyncio
async def test_record_audit_log():
    db = AsyncMock()
    db.add = MagicMock()
    repo = ReportRepository(db)

    user_id = uuid.uuid4()
    log_entry = await repo.record_audit_log(
        user_id=user_id,
        action="EXPORT_REPORT",
        resource="reports",
        ip_address="192.168.1.100",
        user_agent="Mozilla/5.0",
        details={"report_type": "INVENTORY", "format": "EXCEL"},
    )

    assert log_entry.user_id == user_id
    assert log_entry.action == "EXPORT_REPORT"
    assert log_entry.resource == "reports"
    assert log_entry.ip_address == "192.168.1.100"
    assert log_entry.details["format"] == "EXCEL"
    assert db.add.called
    assert db.flush.called
