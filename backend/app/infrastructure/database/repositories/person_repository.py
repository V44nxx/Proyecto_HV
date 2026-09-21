"""
Person repository: database operations for Person, ContactInformation,
Educations, WorkExperiences, ExperienceSummary, Languages, and ExtractedFields.
"""

import uuid
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.infrastructure.database.models.document_models import ExtractedField
from app.infrastructure.database.models.person_models import (
    ContactInformation,
    Person,
)
from app.infrastructure.database.models.resume_models import (
    Education,
    ExperienceSummary,
    Language,
    WorkExperience,
)

logger = structlog.get_logger(__name__)


class PersonRepository:
    """Handles persistence operations for candidate persons and resume details."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_by_id(self, person_id: uuid.UUID) -> Person | None:
        """Fetch person by primary key."""
        stmt = select(Person).where(Person.id == person_id, Person.deleted_at.is_(None))
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_identification(
        self, identification_type: str | None, identification_number: str | None
    ) -> Person | None:
        """
        Fetch person by unique combination of identification type and number.
        """
        if not identification_type or not identification_number:
            return None
        stmt = select(Person).where(
            Person.identification_type == identification_type,
            Person.identification_number == identification_number,
            Person.deleted_at.is_(None),
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_or_update_person(self, person: Person) -> Person:
        """
        Idempotently create or update a person based on identification.
        """
        existing = await self.get_by_identification(
            person.identification_type, person.identification_number
        )
        if existing:
            # Update fields if new information was provided
            for attr in [
                "first_surname", "second_surname", "first_name", "middle_name",
                "sex", "nationality", "birth_date", "birth_country",
                "birth_department", "birth_municipality", "military_card_number",
                "military_card_district", "military_card_class",
            ]:
                new_val = getattr(person, attr)
                if new_val is not None:
                    setattr(existing, attr, new_val)
            await self._db.flush()
            return existing

        self._db.add(person)
        await self._db.flush()
        await self._db.refresh(person)
        logger.info(
            "person_record_created",
            person_id=str(person.id),
            id_num=person.identification_number,
        )
        return person

    async def save_contact_information(
        self, contact: ContactInformation
    ) -> ContactInformation:
        """Create or update contact information for a person."""
        stmt = select(ContactInformation).where(
            ContactInformation.person_id == contact.person_id
        )
        result = await self._db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            for attr in ["address", "country", "department", "municipality", "telephone", "mobile_phone", "email"]:
                val = getattr(contact, attr)
                if val is not None:
                    setattr(existing, attr, val)
            await self._db.flush()
            return existing

        self._db.add(contact)
        await self._db.flush()
        return contact

    async def save_educations(
        self, educations: list[Education]
    ) -> list[Education]:
        """Bulk save education records."""
        if not educations:
            return []
        self._db.add_all(educations)
        await self._db.flush()
        return educations

    async def save_work_experiences(
        self, experiences: list[WorkExperience]
    ) -> list[WorkExperience]:
        """Bulk save work experience records."""
        if not experiences:
            return []
        self._db.add_all(experiences)
        await self._db.flush()
        return experiences

    async def save_experience_summary(
        self, summary: ExperienceSummary
    ) -> ExperienceSummary:
        """Create or update experience summary for a person."""
        stmt = select(ExperienceSummary).where(
            ExperienceSummary.person_id == summary.person_id
        )
        result = await self._db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            for attr in [
                "public_years", "public_months", "private_years", "private_months",
                "independent_years", "independent_months", "total_years", "total_months",
            ]:
                setattr(existing, attr, getattr(summary, attr))
            await self._db.flush()
            return existing

        self._db.add(summary)
        await self._db.flush()
        return summary

    async def save_languages(
        self, languages: list[Language]
    ) -> list[Language]:
        """Bulk save language records."""
        if not languages:
            return []
        self._db.add_all(languages)
        await self._db.flush()
        return languages

    async def save_extracted_fields(
        self, fields: list[ExtractedField]
    ) -> list[ExtractedField]:
        """Bulk save extracted fields for traceability."""
        if not fields:
            return []
        self._db.add_all(fields)
        await self._db.flush()
        return fields

    async def get_person_with_details(self, person_id: uuid.UUID) -> Person | None:
        """Fetch person with all eager-loaded relations."""
        stmt = (
            select(Person)
            .where(Person.id == person_id, Person.deleted_at.is_(None))
            .options(
                selectinload(Person.contact_information),
                selectinload(Person.educations),
                selectinload(Person.work_experiences),
                selectinload(Person.experience_summary),
                selectinload(Person.languages),
            )
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()
