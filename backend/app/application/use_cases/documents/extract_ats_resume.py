"""
Extract ATS Resume use case.

Executes structured semantic data extraction for free-form resumes in Spanish
and English, maps fields to the canonical domain model, persists candidate
records, and links the document.
"""

import uuid
import structlog

from app.application.interfaces.storage_provider import StorageProvider
from app.application.use_cases.documents.exceptions import DocumentNotFoundError
from app.config.constants import JobStatus
from app.domain.entities.canonical_resume import CanonicalResume
from app.infrastructure.database.models.document_models import ExtractedField
from app.infrastructure.database.models.person_models import (
    ContactInformation,
    Person,
)
from app.infrastructure.database.models.resume_models import (
    Education,
    Language,
    WorkExperience,
)
from app.infrastructure.database.repositories.document_repository import DocumentRepository
from app.infrastructure.database.repositories.person_repository import PersonRepository
from app.infrastructure.extraction.ats_extractor import AtsResumeExtractor
from app.infrastructure.extraction.pdf_text_extractor import PDFTextExtractor

logger = structlog.get_logger(__name__)


class ExtractAtsResumeUseCase:
    """
    Coordinates free-form ATS resume extraction and relational persistence.
    """

    def __init__(
        self,
        document_repo: DocumentRepository,
        person_repo: PersonRepository,
        storage_provider: StorageProvider,
        extractor: AtsResumeExtractor | None = None,
    ) -> None:
        self._doc_repo = document_repo
        self._person_repo = person_repo
        self._storage = storage_provider
        self._extractor = extractor or AtsResumeExtractor()

    async def execute(
        self,
        document_id: uuid.UUID,
        job_id: uuid.UUID | None = None,
    ) -> CanonicalResume:
        doc = await self._doc_repo.get_by_id(document_id)
        if not doc:
            raise DocumentNotFoundError(f"Documento con ID {document_id} no encontrado.")

        # 1. Gather text: from extractions table or native PDF extractor fallback
        extractions = await self._doc_repo.get_extractions_for_document(document_id)
        full_text = ""
        page_texts: list[str] = []
        extraction_map: dict[int, uuid.UUID] = {}

        if extractions:
            for idx, e in enumerate(extractions):
                raw = e.raw_text or ""
                page_texts.append(raw)
                extraction_map[idx + 1] = e.id
            full_text = "\n\n".join(page_texts)
        else:
            pdf_bytes = await self._storage.get(doc.storage_key)
            native_res = PDFTextExtractor.extract_native_document(pdf_bytes)
            page_texts = [p.full_text for p in native_res.pages]
            full_text = "\n\n".join(page_texts)

        # 2. Run ATS extractor
        canonical_resume = self._extractor.extract(
            full_text=full_text, page_texts=page_texts
        )

        # 3. Create or update Person record
        person_model = Person(
            identification_type=canonical_resume.person.identification_type,
            identification_number=canonical_resume.person.identification_number,
            first_surname=canonical_resume.person.first_surname,
            second_surname=canonical_resume.person.second_surname,
            first_name=canonical_resume.person.first_name,
            middle_name=canonical_resume.person.middle_name,
            sex=canonical_resume.person.sex,
            nationality=canonical_resume.person.nationality,
            birth_date=canonical_resume.person.birth_date,
            birth_country=canonical_resume.person.birth_country,
            birth_department=canonical_resume.person.birth_department,
            birth_municipality=canonical_resume.person.birth_municipality,
        )
        saved_person = await self._person_repo.create_or_update_person(person_model)

        # 4. Link Document to Person
        await self._doc_repo.link_person_to_document(document_id, saved_person.id)

        # 5. Persist Contact Information
        contact_model = ContactInformation(
            person_id=saved_person.id,
            address=canonical_resume.contact.address,
            country=canonical_resume.contact.country,
            department=canonical_resume.contact.department,
            municipality=canonical_resume.contact.municipality,
            telephone=canonical_resume.contact.telephone,
            mobile_phone=canonical_resume.contact.mobile_phone,
            email=canonical_resume.contact.email,
        )
        await self._person_repo.save_contact_information(contact_model)

        # 6. Persist Educations
        education_models = [
            Education(
                person_id=saved_person.id,
                level=e.level,
                institution=e.institution,
                program=e.program,
                academic_modality=e.academic_modality,
                semesters_count=e.semesters_count,
                graduation_status=e.graduation_status,
                degree_title=e.degree_title,
                professional_card_no=e.professional_card_no,
                completion_month=e.completion_month,
                completion_year=e.completion_year,
                country=e.country,
                department=e.department,
                municipality=e.municipality,
                source_page=e.source_page,
            )
            for e in canonical_resume.educations
        ]
        await self._person_repo.save_educations(education_models)

        # 7. Persist Work Experiences
        experience_models = [
            WorkExperience(
                person_id=saved_person.id,
                company_name=w.company_name,
                sector=w.sector,
                position=w.position,
                department_unit=w.department_unit,
                country=w.country,
                department=w.department,
                municipality=w.municipality,
                address=w.address,
                telephone=w.telephone,
                entity_email=w.entity_email,
                start_date=w.start_date,
                end_date=w.end_date,
                is_current=w.is_current,
                responsibilities=w.responsibilities,
                source_page=w.source_page,
            )
            for w in canonical_resume.work_experiences
        ]
        await self._person_repo.save_work_experiences(experience_models)

        # 8. Persist Languages
        language_models = [
            Language(
                person_id=saved_person.id,
                language_name=l.language_name,
                speaking=l.speaking,
                reading=l.reading,
                writing=l.writing,
                source_page=l.source_page,
            )
            for l in canonical_resume.languages
        ]
        await self._person_repo.save_languages(language_models)

        # 9. Persist Extracted Fields for traceability
        if extraction_map and canonical_resume.extracted_fields:
            field_models: list[ExtractedField] = []
            for item in canonical_resume.extracted_fields:
                ext_id = extraction_map.get(item.page_number) or list(extraction_map.values())[0]
                field_models.append(
                    ExtractedField(
                        extraction_id=ext_id,
                        field_name=item.field_name,
                        raw_value=item.raw_value,
                        normalized_value=item.normalized_value,
                        page_number=item.page_number,
                        bounding_box=item.bounding_box,
                        confidence=item.confidence,
                    )
                )
            await self._person_repo.save_extracted_fields(field_models)

        # 10. Update processing job tracking
        job = None
        if job_id:
            job = await self._doc_repo.get_processing_job(job_id)
        if not job:
            job = await self._doc_repo.get_latest_job_for_document(document_id)

        if job:
            await self._doc_repo.update_processing_job(
                job_id=job.id,
                status=JobStatus.PROCESSING.value,
                current_step="ats_extraction",
                progress_pct=70,
            )

        logger.info(
            "ats_extraction_completed",
            document_id=str(document_id),
            person_id=str(saved_person.id),
            educations_count=len(education_models),
            experiences_count=len(experience_models),
            skills_count=len(canonical_resume.metadata.get("skills", [])),
        )

        return canonical_resume
