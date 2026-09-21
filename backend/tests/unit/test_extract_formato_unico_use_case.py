"""
Unit tests for ExtractFormatoUnicoUseCase and GetCanonicalResumeUseCase.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock
from datetime import date
import pytest

from app.application.use_cases.documents.exceptions import DocumentNotFoundError
from app.application.use_cases.documents.extract_formato_unico import ExtractFormatoUnicoUseCase
from app.application.use_cases.documents.get_canonical_resume import GetCanonicalResumeUseCase
from app.config.constants import DocumentType, JobStatus
from app.domain.entities.canonical_resume import (
    CanonicalContact,
    CanonicalEducation,
    CanonicalExperienceSummary,
    CanonicalLanguage,
    CanonicalPerson,
    CanonicalResume,
    CanonicalWorkExperience,
    ExtractedFieldItem,
)
from app.infrastructure.database.models.document_models import Document, DocumentExtraction, ProcessingJob
from app.infrastructure.database.models.person_models import Person, ContactInformation
from app.infrastructure.database.models.resume_models import (
    Education,
    ExperienceSummary,
    Language,
    WorkExperience,
)


@pytest.mark.asyncio
async def test_extract_formato_unico_doc_not_found():
    doc_repo = AsyncMock()
    doc_repo.get_by_id.return_value = None
    person_repo = AsyncMock()
    storage = AsyncMock()

    use_case = ExtractFormatoUnicoUseCase(
        document_repo=doc_repo,
        person_repo=person_repo,
        storage_provider=storage,
    )

    with pytest.raises(DocumentNotFoundError):
        await use_case.execute(document_id=uuid.uuid4())


@pytest.mark.asyncio
async def test_extract_formato_unico_success_with_extractions():
    doc_id = uuid.uuid4()
    person_id = uuid.uuid4()
    job_id = uuid.uuid4()
    ext_id = uuid.uuid4()

    mock_doc = Document(
        id=doc_id,
        original_filename="cv_dafp.pdf",
        storage_key="docs/cv_dafp.pdf",
        file_size_bytes=1024,
        mime_type="application/pdf",
        checksum_sha256="abc12345",
        document_type=DocumentType.FORMATO_UNICO.value,
    )

    mock_ext = DocumentExtraction(
        id=ext_id,
        document_id=doc_id,
        ocr_provider="NATIVE_PDF",
        raw_text="FORMATO UNICO HOJA DE VIDA\nCARLOS PEREZ\nCC: 12345678",
    )

    saved_person = Person(
        id=person_id,
        identification_type="CC",
        identification_number="12345678",
        first_surname="PEREZ",
        first_name="CARLOS",
    )

    mock_job = ProcessingJob(
        id=job_id,
        document_id=doc_id,
        status=JobStatus.PROCESSING.value,
        progress_pct=40,
    )

    doc_repo = AsyncMock()
    doc_repo.get_by_id.return_value = mock_doc
    doc_repo.get_extractions_for_document.return_value = [mock_ext]
    doc_repo.get_processing_job.return_value = mock_job

    person_repo = AsyncMock()
    person_repo.create_or_update_person.return_value = saved_person

    mock_extractor = MagicMock()
    sample_resume = CanonicalResume(
        person=CanonicalPerson(
            identification_type="CC",
            identification_number="12345678",
            first_surname="PEREZ",
            first_name="CARLOS",
        ),
        contact=CanonicalContact(
            email="carlos@example.com",
            telephone="3001234567",
        ),
        educations=[
            CanonicalEducation(
                level="UNDERGRADUATE",
                institution="Universidad Nacional",
                degree_title="Ingeniero",
            )
        ],
        work_experiences=[
            CanonicalWorkExperience(
                company_name="MinTIC",
                sector="PUBLIC",
                position="Ingeniero",
                start_date=date(2020, 1, 1),
            )
        ],
        experience_summary=CanonicalExperienceSummary(
            public_years=3,
            total_years=3,
        ),
        languages=[
            CanonicalLanguage(
                language_name="INGLES",
                speaking="BIEN",
            )
        ],
        extracted_fields=[
            ExtractedFieldItem(
                field_name="identification_number",
                raw_value="12345678",
                normalized_value="12345678",
                page_number=1,
            )
        ],
    )
    mock_extractor.extract.return_value = sample_resume
    storage = AsyncMock()

    use_case = ExtractFormatoUnicoUseCase(
        document_repo=doc_repo,
        person_repo=person_repo,
        storage_provider=storage,
        extractor=mock_extractor,
    )

    result = await use_case.execute(document_id=doc_id, job_id=job_id)

    assert result == sample_resume
    doc_repo.link_person_to_document.assert_awaited_once_with(doc_id, person_id)
    person_repo.save_contact_information.assert_awaited_once()
    person_repo.save_educations.assert_awaited_once()
    person_repo.save_work_experiences.assert_awaited_once()
    person_repo.save_experience_summary.assert_awaited_once()
    person_repo.save_languages.assert_awaited_once()
    person_repo.save_extracted_fields.assert_awaited_once()
    doc_repo.update_processing_job.assert_awaited_once_with(
        job_id=job_id,
        status=JobStatus.PROCESSING.value,
        current_step="formato_unico_extraction",
        progress_pct=70,
    )


@pytest.mark.asyncio
async def test_get_canonical_resume_use_case_not_found():
    doc_repo = AsyncMock()
    doc_repo.get_by_id.return_value = None
    person_repo = AsyncMock()

    use_case = GetCanonicalResumeUseCase(document_repo=doc_repo, person_repo=person_repo)
    with pytest.raises(DocumentNotFoundError):
        await use_case.execute(uuid.uuid4())


@pytest.mark.asyncio
async def test_get_canonical_resume_use_case_no_person():
    doc_id = uuid.uuid4()
    mock_doc = Document(
        id=doc_id,
        original_filename="file.pdf",
        storage_key="k",
        file_size_bytes=1024,
        mime_type="application/pdf",
        checksum_sha256="abc12345",
        person_id=None,
    )
    doc_repo = AsyncMock()
    doc_repo.get_by_id.return_value = mock_doc
    person_repo = AsyncMock()

    use_case = GetCanonicalResumeUseCase(document_repo=doc_repo, person_repo=person_repo)
    result = await use_case.execute(doc_id)
    assert result is None


@pytest.mark.asyncio
async def test_get_canonical_resume_use_case_success():
    doc_id = uuid.uuid4()
    person_id = uuid.uuid4()
    mock_doc = Document(
        id=doc_id,
        original_filename="file.pdf",
        storage_key="k",
        file_size_bytes=1024,
        mime_type="application/pdf",
        checksum_sha256="abc12345",
        person_id=person_id,
    )

    mock_person = Person(
        id=person_id,
        identification_type="CC",
        identification_number="12345678",
        first_surname="PEREZ",
        first_name="CARLOS",
    )
    mock_person.contact_information = ContactInformation(
        id=uuid.uuid4(),
        person_id=person_id,
        email="carlos@example.com",
    )
    mock_person.educations = [
        Education(id=uuid.uuid4(), person_id=person_id, level="UNDERGRADUATE", degree_title="Ingeniero")
    ]
    mock_person.work_experiences = [
        WorkExperience(id=uuid.uuid4(), person_id=person_id, company_name="Empresa X", position="Dev")
    ]
    mock_person.experience_summary = ExperienceSummary(
        id=uuid.uuid4(), person_id=person_id, total_years=5
    )
    mock_person.languages = [
        Language(id=uuid.uuid4(), person_id=person_id, language_name="INGLES")
    ]

    doc_repo = AsyncMock()
    doc_repo.get_by_id.return_value = mock_doc

    person_repo = AsyncMock()
    person_repo.get_person_with_details.return_value = mock_person

    use_case = GetCanonicalResumeUseCase(document_repo=doc_repo, person_repo=person_repo)
    result = await use_case.execute(doc_id)

    assert result is not None
    assert result.identification_number == "12345678"
    assert result.contact_information.email == "carlos@example.com"
    assert len(result.educations) == 1
    assert len(result.work_experiences) == 1
    assert len(result.languages) == 1
    assert result.experience_summary.total_years == 5
