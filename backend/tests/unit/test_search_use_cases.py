"""
Unit tests for Search use cases:
- SearchCandidatesUseCase
- GetCandidateDetailUseCase
- GetSearchFacetsUseCase
- GetFilterOptionsUseCase
- ClassifyCandidateProfessionUseCase
"""

from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock
import uuid
import pytest

from app.application.use_cases.search import (
    CandidateNotFoundError,
    ClassifyCandidateProfessionUseCase,
    GetCandidateDetailUseCase,
    GetFilterOptionsUseCase,
    GetSearchFacetsUseCase,
    SearchCandidatesUseCase,
)
from app.infrastructure.database.models.document_models import Document
from app.infrastructure.database.models.person_models import (
    ContactInformation,
    Person,
    Profession,
    ProfessionalCategory,
)
from app.infrastructure.database.models.resume_models import (
    Certification,
    Education,
    ExperienceSummary,
    Language,
    ProfessionalProfile,
    WorkExperience,
)


@pytest.mark.asyncio
async def test_search_candidates_use_case():
    search_repo = AsyncMock()
    person_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    mock_person = Person(
        id=person_id,
        first_name="Carlos",
        middle_name="Alberto",
        first_surname="Gomez",
        second_surname="Perez",
        identification_type="CC",
        identification_number="12345678",
        created_at=now,
    )
    mock_person.contact_information = ContactInformation(
        person_id=person_id,
        email="carlos.gomez@example.com",
        telephone="3110001122",
        municipality="Medellín",
        department="Antioquia",
    )
    mock_person.primary_profession = Profession(
        id=uuid.uuid4(),
        category_id=uuid.uuid4(),
        name="Ingeniería de Sistemas y Computación",
    )
    mock_person.educations = [
        Education(
            person_id=person_id,
            level="UNDERGRADUATE",
            institution="Universidad de Antioquia",
            degree_title="Ingeniero de Sistemas",
            completion_year=2018,
        )
    ]
    mock_person.work_experiences = [
        WorkExperience(
            person_id=person_id,
            company_name="Tech Corp",
            position="Backend Engineer",
        )
    ]
    mock_person.experience_summary = ExperienceSummary(
        person_id=person_id,
        total_years=6,
        total_months=4,
    )
    mock_person.professional_profile = ProfessionalProfile(
        person_id=person_id,
        skills=["Python", "FastAPI", "Docker"],
        summary="Senior backend developer",
    )
    mock_person.documents = [
        Document(
            id=uuid.uuid4(),
            person_id=person_id,
            original_filename="cv_carlos.pdf",
            file_size_bytes=1024,
            mime_type="application/pdf",
            storage_key="docs/cv.pdf",
            checksum_sha256="abc12345",
        )
    ]

    search_repo.search_candidates.return_value = ([mock_person], 1)

    use_case = SearchCandidatesUseCase(search_repo=search_repo)
    response = await use_case.execute(
        filters={"q": "Carlos"},
        page=1,
        page_size=10,
        sort_by="name",
        sort_order="asc",
    )

    assert response.total == 1
    assert response.page == 1
    assert response.total_pages == 1
    assert len(response.items) == 1

    item = response.items[0]
    assert item.id == person_id
    assert item.full_name == "Carlos Alberto Gomez Perez"
    assert item.identification_number == "12345678"
    assert item.primary_profession == "Ingeniería de Sistemas y Computación"
    assert item.email == "carlos.gomez@example.com"
    assert item.total_experience_years == 6
    assert item.top_education == "Ingeniero de Sistemas"
    assert "Python" in item.skills
    assert item.documents_count == 1


@pytest.mark.asyncio
async def test_get_candidate_detail_not_found():
    search_repo = AsyncMock()
    search_repo.get_candidate_detail.return_value = None

    use_case = GetCandidateDetailUseCase(search_repo=search_repo)
    with pytest.raises(CandidateNotFoundError):
        await use_case.execute(uuid.uuid4())


@pytest.mark.asyncio
async def test_get_candidate_detail_success():
    search_repo = AsyncMock()
    person_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    mock_person = Person(
        id=person_id,
        first_name="Laura",
        first_surname="Restrepo",
        identification_type="CC",
        identification_number="87654321",
        birth_date=date(1990, 5, 20),
        created_at=now,
    )
    mock_person.contact_information = ContactInformation(
        person_id=person_id,
        email="laura@hospital.org",
        municipality="Bogotá",
        department="Bogotá D.C.",
    )
    mock_person.educations = [
        Education(
            id=uuid.uuid4(),
            person_id=person_id,
            level="UNDERGRADUATE",
            degree_title="Médico Cirujano",
            institution="Universidad Nacional",
        )
    ]
    mock_person.work_experiences = [
        WorkExperience(
            id=uuid.uuid4(),
            person_id=person_id,
            company_name="Hospital San Juan",
            position="Médico de Urgencias",
        )
    ]
    mock_person.experience_summary = ExperienceSummary(
        person_id=person_id,
        total_years=5,
        total_months=0,
    )
    mock_person.languages = [
        Language(
            id=uuid.uuid4(),
            person_id=person_id,
            language_name="INGLES",
            speaking="AVANZADO",
        )
    ]
    mock_person.certifications = [
        Certification(
            id=uuid.uuid4(),
            person_id=person_id,
            name="Soporte Vital Avanzado (ACLS)",
        )
    ]
    mock_person.professional_profile = ProfessionalProfile(
        person_id=person_id,
        summary="Médica especialista en medicina de emergencias",
        skills=["Urgencias", "Cirugía Menor", "ACLS"],
    )
    mock_person.documents = []

    search_repo.get_candidate_detail.return_value = mock_person

    use_case = GetCandidateDetailUseCase(search_repo=search_repo)
    res = await use_case.execute(person_id)

    assert res.id == person_id
    assert res.full_name == "Laura Restrepo"
    assert res.contact["email"] == "laura@hospital.org"
    assert len(res.educations) == 1
    assert res.educations[0]["degree_title"] == "Médico Cirujano"
    assert len(res.work_experiences) == 1
    assert len(res.languages) == 1
    assert len(res.certifications) == 1
    assert "ACLS" in res.skills


@pytest.mark.asyncio
async def test_get_search_facets_use_case():
    search_repo = AsyncMock()
    search_repo.get_search_facets.return_value = {
        "total_candidates": 100,
        "by_category": {"Ingeniería y Tecnología": 60, "Ciencias de la Salud": 40},
        "by_profession": {"Ingeniería de Sistemas y Computación": 45},
        "by_academic_level": {"UNDERGRADUATE": 70, "MASTER": 30},
        "by_department": {"Bogotá D.C.": 50, "Antioquia": 30},
    }

    use_case = GetSearchFacetsUseCase(search_repo=search_repo)
    res = await use_case.execute()

    assert res.total_candidates == 100
    assert res.by_category["Ingeniería y Tecnología"] == 60
    assert res.by_profession["Ingeniería de Sistemas y Computación"] == 45


@pytest.mark.asyncio
async def test_get_filter_options_use_case():
    search_repo = AsyncMock()
    mock_cat = ProfessionalCategory(
        id=uuid.uuid4(),
        name="Ingeniería y Tecnología",
        description="Sector IT",
    )
    mock_prof = Profession(
        id=uuid.uuid4(),
        category_id=mock_cat.id,
        name="Ingeniería de Sistemas",
        aliases=["IT"],
        is_active=True,
    )
    mock_cat.professions = [mock_prof]

    search_repo.list_categories_with_professions.return_value = [mock_cat]

    use_case = GetFilterOptionsUseCase(search_repo=search_repo)
    res = await use_case.execute()

    assert len(res.categories) == 1
    assert res.categories[0].name == "Ingeniería y Tecnología"
    assert len(res.categories[0].professions) == 1
    assert res.categories[0].professions[0].name == "Ingeniería de Sistemas"
    assert "Bogotá D.C." in res.departments
    assert "UNDERGRADUATE" in res.academic_levels


@pytest.mark.asyncio
async def test_classify_candidate_profession_use_case():
    db = AsyncMock()
    search_repo = AsyncMock()
    person_id = uuid.uuid4()

    mock_person = Person(id=person_id)
    mock_person.educations = [
        Education(person_id=person_id, level="UNDERGRADUATE", degree_title="Ingeniería de Software")
    ]
    mock_person.work_experiences = [
        WorkExperience(person_id=person_id, position="Lead Backend Architect")
    ]
    mock_person.professional_profile = ProfessionalProfile(
        person_id=person_id,
        summary="Expert in software engineering and cloud",
    )
    search_repo.get_candidate_detail.return_value = mock_person

    # Mock DB query for category and profession
    cat_id = uuid.uuid4()
    prof_id = uuid.uuid4()
    mock_cat = ProfessionalCategory(id=cat_id, name="Ingeniería y Tecnología")
    mock_prof = Profession(id=prof_id, category_id=cat_id, name="Ingeniería de Sistemas y Computación")

    cat_result = MagicMock()
    cat_result.scalar_one_or_none.return_value = mock_cat

    prof_result = MagicMock()
    prof_result.scalar_one_or_none.return_value = mock_prof

    db.execute.side_effect = [cat_result, prof_result]

    use_case = ClassifyCandidateProfessionUseCase(db=db, search_repo=search_repo)
    res = await use_case.execute(person_id)

    assert res.person_id == person_id
    assert res.applied is True
    assert res.category_name == "Ingeniería y Tecnología"
    assert res.profession_name == "Ingeniería de Sistemas y Computación"
    assert res.confidence >= 0.6
    assert mock_person.primary_profession_id == prof_id
    assert mock_person.primary_category_id == cat_id
    assert db.flush.called
