"""
Search candidates use case.
"""

import math
from typing import Any
import structlog

from app.infrastructure.database.models.person_models import Person
from app.infrastructure.database.repositories.search_repository import SearchRepository
from app.presentation.schemas.search_schemas import (
    CandidateSearchResponse,
    CandidateSummaryItem,
)

logger = structlog.get_logger(__name__)


class SearchCandidatesUseCase:
    """Coordinates advanced multi-criteria candidate search and pagination formatting."""

    def __init__(self, search_repo: SearchRepository) -> None:
        self._search_repo = search_repo

    async def execute(
        self,
        filters: dict[str, Any],
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> CandidateSearchResponse:
        candidates, total = await self._search_repo.search_candidates(
            filters=filters,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        items: list[CandidateSummaryItem] = []
        for p in candidates:
            # Build full name
            parts = [p.first_name, p.middle_name, p.first_surname, p.second_surname]
            full_name = " ".join(part for part in parts if part) or "Sin Nombre"

            # Primary profession and category
            prof_name = p.primary_profession.name if p.primary_profession else None
            cat_name = p.primary_category.name if getattr(p, "primary_category", None) else None

            # Contact
            email = p.contact_information.email if p.contact_information else None
            telephone = (
                p.contact_information.mobile_phone or p.contact_information.telephone
                if p.contact_information
                else None
            )
            municipality = p.contact_information.municipality if p.contact_information else None
            department = p.contact_information.department if p.contact_information else None

            # Total experience
            exp_years = p.experience_summary.total_years if p.experience_summary else 0

            # Highest/most recent education
            top_edu = None
            if p.educations:
                # Prioritize undergraduate/postgraduate
                sorted_edus = sorted(
                    p.educations,
                    key=lambda e: (e.completion_year or 0),
                    reverse=True,
                )
                top_edu = sorted_edus[0].degree_title or sorted_edus[0].institution

            # Skills
            skills = []
            if p.professional_profile and p.professional_profile.skills:
                raw_skills = p.professional_profile.skills
                if isinstance(raw_skills, list):
                    skills = raw_skills
                elif isinstance(raw_skills, str):
                    import json
                    try:
                        skills = json.loads(raw_skills)
                    except Exception:
                        skills = [s.strip() for s in raw_skills.split(",")]

            items.append(
                CandidateSummaryItem(
                    id=p.id,
                    identification_type=p.identification_type,
                    identification_number=p.identification_number,
                    full_name=full_name,
                    primary_profession=prof_name,
                    primary_category=cat_name,
                    email=email,
                    telephone=telephone,
                    municipality=municipality,
                    department=department,
                    total_experience_years=exp_years,
                    top_education=top_edu,
                    skills=skills,
                    documents_count=len(p.documents) if p.documents else 0,
                    created_at=p.created_at,
                )
            )

        total_pages = math.ceil(total / page_size) if page_size > 0 else 1

        return CandidateSearchResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1,
        )
