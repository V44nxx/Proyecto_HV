"""
Review field use case: accepts, corrects, or rejects an individual extracted field.
Propagates validated corrections to canonical candidate entities (Person, Contact).
"""

import uuid
import structlog

from app.application.use_cases.documents.exceptions import DocumentNotFoundError
from app.config.constants import ReviewStatus
from app.infrastructure.database.models.document_models import ExtractedField
from app.infrastructure.database.repositories.document_repository import DocumentRepository
from app.infrastructure.database.repositories.person_repository import PersonRepository
from app.infrastructure.database.repositories.review_repository import ReviewRepository

logger = structlog.get_logger(__name__)


class ReviewFieldUseCase:
    """Handles review decisions on extracted fields with audit logging and propagation."""

    def __init__(
        self,
        document_repo: DocumentRepository,
        person_repo: PersonRepository,
        review_repo: ReviewRepository,
    ) -> None:
        self._doc_repo = document_repo
        self._person_repo = person_repo
        self._review_repo = review_repo

    async def accept_field(
        self,
        document_id: uuid.UUID,
        field_id: uuid.UUID,
        reviewer_id: uuid.UUID | None = None,
    ) -> ExtractedField:
        doc = await self._doc_repo.get_by_id(document_id)
        if not doc:
            raise DocumentNotFoundError(f"Documento con ID {document_id} no encontrado.")

        field = await self._review_repo.get_field_by_id(field_id)
        if not field:
            raise DocumentNotFoundError(f"Campo con ID {field_id} no encontrado.")

        updated = await self._review_repo.update_field_status(
            field_id=field_id,
            review_status=ReviewStatus.ACCEPTED.value,
            reviewer_id=reviewer_id,
        )

        await self._review_repo.record_audit_log(
            action="FIELD_ACCEPTED",
            resource="extracted_fields",
            user_id=reviewer_id,
            resource_id=field_id,
            details={
                "document_id": str(document_id),
                "field_name": field.field_name,
                "value": field.normalized_value or field.raw_value,
            },
        )

        return updated

    async def correct_field(
        self,
        document_id: uuid.UUID,
        field_id: uuid.UUID,
        corrected_value: str,
        note: str | None = None,
        reviewer_id: uuid.UUID | None = None,
    ) -> ExtractedField:
        doc = await self._doc_repo.get_by_id(document_id)
        if not doc:
            raise DocumentNotFoundError(f"Documento con ID {document_id} no encontrado.")

        field = await self._review_repo.get_field_by_id(field_id)
        if not field:
            raise DocumentNotFoundError(f"Campo con ID {field_id} no encontrado.")

        original_val = field.normalized_value or field.raw_value
        updated = await self._review_repo.update_field_status(
            field_id=field_id,
            review_status=ReviewStatus.CORRECTED.value,
            corrected_value=corrected_value,
            correction_note=note,
            reviewer_id=reviewer_id,
        )

        # Propagate correction to canonical Person / Contact entity if linked
        if doc.person_id:
            person = await self._person_repo.get_person_with_details(doc.person_id)
            if person:
                name_attrs = [
                    "first_name", "middle_name", "first_surname", "second_surname",
                    "identification_number", "identification_type",
                ]
                contact_attrs = [
                    "email", "telephone", "mobile_phone", "address",
                    "municipality", "department", "country",
                ]

                if field.field_name in name_attrs:
                    setattr(person, field.field_name, corrected_value)
                elif field.field_name in contact_attrs and person.contact_information:
                    setattr(person.contact_information, field.field_name, corrected_value)

        await self._review_repo.record_audit_log(
            action="FIELD_CORRECTED",
            resource="extracted_fields",
            user_id=reviewer_id,
            resource_id=field_id,
            details={
                "document_id": str(document_id),
                "field_name": field.field_name,
                "original_value": original_val,
                "corrected_value": corrected_value,
                "note": note,
            },
        )

        return updated

    async def reject_field(
        self,
        document_id: uuid.UUID,
        field_id: uuid.UUID,
        reason: str | None = None,
        reviewer_id: uuid.UUID | None = None,
    ) -> ExtractedField:
        doc = await self._doc_repo.get_by_id(document_id)
        if not doc:
            raise DocumentNotFoundError(f"Documento con ID {document_id} no encontrado.")

        field = await self._review_repo.get_field_by_id(field_id)
        if not field:
            raise DocumentNotFoundError(f"Campo con ID {field_id} no encontrado.")

        updated = await self._review_repo.update_field_status(
            field_id=field_id,
            review_status=ReviewStatus.REJECTED.value,
            correction_note=reason,
            reviewer_id=reviewer_id,
        )

        await self._review_repo.record_audit_log(
            action="FIELD_REJECTED",
            resource="extracted_fields",
            user_id=reviewer_id,
            resource_id=field_id,
            details={
                "document_id": str(document_id),
                "field_name": field.field_name,
                "reason": reason,
            },
        )

        return updated
