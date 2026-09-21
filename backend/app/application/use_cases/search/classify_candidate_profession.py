"""
Classify candidate profession use case.
"""

from typing import Any
import uuid
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.use_cases.search.exceptions import CandidateNotFoundError
from app.domain.services.profession_classifier import ProfessionClassifier
from app.infrastructure.database.models.person_models import (
    Profession,
    ProfessionalCategory,
)
from app.infrastructure.database.repositories.search_repository import SearchRepository
from app.presentation.schemas.search_schemas import ClassifyProfessionResponse

logger = structlog.get_logger(__name__)


class ClassifyCandidateProfessionUseCase:
    """
    Analyzes a candidate's academic and work history to determine and assign
    their canonical profession and category.
    """

    def __init__(self, db: AsyncSession, search_repo: SearchRepository) -> None:
        self._db = db
        self._search_repo = search_repo

    async def execute(self, person_id: uuid.UUID) -> ClassifyProfessionResponse:
        person = await self._search_repo.get_candidate_detail(person_id)
        if not person:
            raise CandidateNotFoundError(person_id)

        # Collect text inputs from education, experiences, and summary
        texts: list[str | None] = []
        for e in person.educations:
            texts.append(e.degree_title)
            texts.append(e.program)

        for w in person.work_experiences:
            texts.append(w.position)

        if person.professional_profile:
            texts.append(person.professional_profile.summary)

        match = ProfessionClassifier.classify(texts)

        applied = False
        if match.confidence >= 0.6:
            # Find matching category and profession
            cat_stmt = select(ProfessionalCategory).where(
                ProfessionalCategory.name == match.category_name
            )
            cat_res = await self._db.execute(cat_stmt)
            category = cat_res.scalar_one_or_none()

            prof_stmt = select(Profession).where(
                Profession.name == match.profession_name
            )
            prof_res = await self._db.execute(prof_stmt)
            profession = prof_res.scalar_one_or_none()

            if profession and category:
                person.primary_profession_id = profession.id
                person.primary_category_id = category.id
                await self._db.flush()
                applied = True
                logger.info(
                    "candidate_profession_classified",
                    person_id=str(person_id),
                    profession=match.profession_name,
                    category=match.category_name,
                    confidence=match.confidence,
                )

        return ClassifyProfessionResponse(
            person_id=person_id,
            category_name=match.category_name,
            profession_name=match.profession_name,
            confidence=match.confidence,
            applied=applied,
        )
