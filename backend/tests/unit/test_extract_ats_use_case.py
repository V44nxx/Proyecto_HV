"""
Unit tests for ExtractAtsResumeUseCase.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock
from datetime import date
import pytest

from app.application.use_cases.documents.exceptions import DocumentNotFoundError
from app.application.use_cases.documents.extract_ats_resume import ExtractAtsResumeUseCase
from app.config.constants import DocumentType, JobStatus
from app.domain.entities.canonical_resume import (
    CanonicalContact,
    CanonicalEducation,
    CanonicalLanguage,
    CanonicalPerson,
    CanonicalResume,
    CanonicalWorkExperience,
    ExtractedFieldItem,
)
from app.infrastructure.database.models.document_models import Document, DocumentExtraction, ProcessingJob
from app.infrastructure.database.models.person_models import Person


@pytest.mark.asyncio
async def test_extract_ats_resume_not_found():
    doc_repo = AsyncMock()
    doc_repo.get_by_id.return_value = None
    person_repo = AsyncMock()
    storage = AsyncMock()

    use_case = ExtractAtsResumeUseCase(
        document_repo=doc_repo,
        person_repo=person_repo,
        storage_provider=storage,
    )

    with pytest.raises(DocumentNotFoundError):
        await use_case.execute(document_id=uuid.uuid4())


@pytest.mark.asyncio
async def test_extract_ats_resume_success():
    doc_id = uuid.uuid4()
    person_id = uuid.uuid4()
    job_id = uuid.uuid4()
    ext_id = uuid.uuid4()

    mock_doc = Document(
        id=doc_id,
        original_filename="resume.pdf",
        storage_key="docs/resume.pdf",
        file_size_bytes=1024,
        mime_type="application/pdf",
        checksum_sha256="12345abc",
        document_type=DocumentType.ATS.value,
    )

    mock_ext = DocumentExtraction(
        id=ext_id,
        document_id=doc_id,
        ocr_provider="NATIVE_PDF",
        raw_text="MARIA LOPEZ\nBackend Engineer\nPython, Docker",
    )

    saved_person = Person(
        id=person_id,
        identification_type="CC",
        identification_number="52894120",
        first_surname="LOPEZ",
        first_name="MARIA",
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
            identification_number="52894120",
            first_surname="LOPEZ",
            first_name="MARIA",
        ),
        contact=CanonicalContact(
            email="maria@techcorp.com",
            telephone="3124567890",
        ),
        educations=[
            CanonicalEducation(
                level="UNDERGRADUATE",
                institution="Universidad de los Andes",
                degree_title="Ingeniera de Sistemas",
                completion_year=2017,
            )
        ],
        work_experiences=[
            CanonicalWorkExperience(
                company_name="TechCorp",
                sector="PRIVATE",
                position="Senior Backend Engineer",
                start_date=date(2021, 1, 1),
                is_current=True,
            )
        ],
        languages=[
            CanonicalLanguage(
                language_name="INGLES",
                speaking="MUY_BIEN",
            )
        ],
        extracted_fields=[
            ExtractedFieldItem(
                field_name="email",
                raw_value="maria@techcorp.com",
                normalized_value="maria@techcorp.com",
                page_number=1,
            )
        ],
        metadata={
            "source_format": "ATS",
            "skills": ["Python", "Docker", "FastAPI"],
        },
    )
    mock_extractor.extract.return_value = sample_resume
    storage = AsyncMock()

    use_case = ExtractAtsResumeUseCase(
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
    person_repo.save_languages.assert_awaited_once()
    person_repo.save_extracted_fields.assert_awaited_once()
    doc_repo.update_processing_job.assert_awaited_once_with(
        job_id=job_id,
        status=JobStatus.PROCESSING.value,
        current_step="ats_extraction",
        progress_pct=70,
    )
