"""
Get candidate detail use case.
"""

from typing import Any
import uuid
import structlog

from app.application.use_cases.search.exceptions import CandidateNotFoundError
from app.infrastructure.database.repositories.search_repository import SearchRepository
from app.presentation.schemas.search_schemas import CandidateFullDetailResponse

logger = structlog.get_logger(__name__)


class GetCandidateDetailUseCase:
    """Retrieves the complete profile and dossier of a candidate."""

    def __init__(self, search_repo: SearchRepository) -> None:
        self._search_repo = search_repo

    async def execute(self, person_id: uuid.UUID) -> CandidateFullDetailResponse:
        p = await self._search_repo.get_candidate_detail(person_id)
        if not p:
            raise CandidateNotFoundError(person_id)

        # Full name
        parts = [p.first_name, p.middle_name, p.first_surname, p.second_surname]
        full_name = " ".join(part for part in parts if part) or "Sin Nombre"

        # Contact
        contact_data = None
        if p.contact_information:
            c = p.contact_information
            contact_data = {
                "id": str(c.id),
                "address": c.address,
                "country": c.country,
                "department": c.department,
                "municipality": c.municipality,
                "telephone": c.telephone,
                "mobile_phone": c.mobile_phone,
                "email": c.email,
            }

        # Educations
        educations_data = []
        for e in p.educations:
            educations_data.append({
                "id": str(e.id),
                "level": e.level,
                "institution": e.institution,
                "program": e.program,
                "degree_title": e.degree_title,
                "completion_month": e.completion_month,
                "completion_year": e.completion_year,
                "graduation_status": e.graduation_status,
                "professional_card_no": e.professional_card_no,
                "country": e.country,
                "department": e.department,
                "municipality": e.municipality,
                "source_page": e.source_page,
            })

        # Work experiences
        experiences_data = []
        for w in p.work_experiences:
            experiences_data.append({
                "id": str(w.id),
                "company_name": w.company_name,
                "sector": w.sector,
                "position": w.position,
                "department_unit": w.department_unit,
                "start_date": w.start_date.isoformat() if w.start_date else None,
                "end_date": w.end_date.isoformat() if w.end_date else None,
                "is_current": w.is_current,
                "responsibilities": w.responsibilities,
                "country": w.country,
                "department": w.department,
                "municipality": w.municipality,
                "source_page": w.source_page,
            })

        # Experience summary
        exp_summary_data = None
        if p.experience_summary:
            s = p.experience_summary
            exp_summary_data = {
                "public_years": s.public_years,
                "public_months": s.public_months,
                "private_years": s.private_years,
                "private_months": s.private_months,
                "independent_years": s.independent_years,
                "independent_months": s.independent_months,
                "total_years": s.total_years,
                "total_months": s.total_months,
            }

        # Languages
        languages_data = []
        for l in p.languages:
            languages_data.append({
                "id": str(l.id),
                "language_name": l.language_name,
                "speaking": l.speaking,
                "reading": l.reading,
                "writing": l.writing,
                "source_page": l.source_page,
            })

        # Certifications
        certifications_data = []
        for cert in p.certifications:
            certifications_data.append({
                "id": str(cert.id),
                "name": cert.name,
                "issuing_entity": cert.issuing_entity,
                "issue_date": cert.issue_date.isoformat() if cert.issue_date else None,
                "expiry_date": cert.expiry_date.isoformat() if cert.expiry_date else None,
                "credential_id": cert.credential_id,
                "source_page": cert.source_page,
            })

        # Skills & Profile
        skills = []
        prof_summary = None
        if p.professional_profile:
            raw_skills = p.professional_profile.skills or []
            if isinstance(raw_skills, list):
                skills = raw_skills
            elif isinstance(raw_skills, str):
                import json
                try:
                    skills = json.loads(raw_skills)
                except Exception:
                    skills = [s.strip() for s in raw_skills.split(",")]
            prof_summary = p.professional_profile.summary

        # Documents
        docs_data = []
        for d in p.documents:
            docs_data.append({
                "id": str(d.id),
                "original_filename": d.original_filename,
                "document_type": d.document_type,
                "file_size_bytes": d.file_size_bytes,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            })

        prof_name = p.primary_profession.name if p.primary_profession else None
        cat_name = p.primary_category.name if getattr(p, "primary_category", None) else None

        return CandidateFullDetailResponse(
            id=p.id,
            identification_type=p.identification_type,
            identification_number=p.identification_number,
            first_surname=p.first_surname,
            second_surname=p.second_surname,
            first_name=p.first_name,
            middle_name=p.middle_name,
            full_name=full_name,
            sex=p.sex,
            nationality=p.nationality,
            birth_date=p.birth_date,
            birth_country=p.birth_country,
            birth_department=p.birth_department,
            birth_municipality=p.birth_municipality,
            military_card_number=p.military_card_number,
            primary_profession=prof_name,
            primary_category=cat_name,
            contact=contact_data,
            educations=educations_data,
            work_experiences=experiences_data,
            experience_summary=exp_summary_data,
            languages=languages_data,
            certifications=certifications_data,
            skills=skills,
            professional_summary=prof_summary,
            documents=docs_data,
            created_at=p.created_at,
        )
