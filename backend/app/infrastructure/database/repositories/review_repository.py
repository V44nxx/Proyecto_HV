"""
Review repository: database operations for ExtractedField inspection,
human-in-the-loop review actions, batch operations, and audit logging.
"""

from datetime import datetime, timezone
from typing import Any
import uuid
import structlog
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.constants import ReviewStatus
from app.infrastructure.database.models.document_models import (
    DocumentExtraction,
    ExtractedField,
)
from app.infrastructure.database.models.user_models import AuditLog

logger = structlog.get_logger(__name__)


class ReviewRepository:
    """Handles data access for human review of extracted document fields."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_field_by_id(self, field_id: uuid.UUID) -> ExtractedField | None:
        """Fetch a single extracted field by ID."""
        stmt = select(ExtractedField).where(ExtractedField.id == field_id)
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_fields_for_document(
        self,
        document_id: uuid.UUID,
        status_filter: str | None = None,
        page_number: int | None = None,
    ) -> list[ExtractedField]:
        """
        Fetch extracted fields linked to a document via its document extractions.
        """
        stmt = (
            select(ExtractedField)
            .join(DocumentExtraction, ExtractedField.extraction_id == DocumentExtraction.id)
            .where(DocumentExtraction.document_id == document_id)
        )

        if status_filter:
            stmt = stmt.where(ExtractedField.review_status == status_filter.upper())
        if page_number is not None:
            stmt = stmt.where(ExtractedField.page_number == page_number)

        stmt = stmt.order_by(ExtractedField.page_number.asc(), ExtractedField.created_at.asc())
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def update_field_status(
        self,
        field_id: uuid.UUID,
        review_status: str,
        corrected_value: str | None = None,
        correction_note: str | None = None,
        reviewer_id: uuid.UUID | None = None,
    ) -> ExtractedField | None:
        """
        Update the review status of an extracted field with optional correction.
        """
        field = await self.get_field_by_id(field_id)
        if not field:
            return None

        now = datetime.now(timezone.utc)
        field.review_status = review_status.upper()
        field.corrected_by = reviewer_id
        field.corrected_at = now

        if corrected_value is not None:
            field.corrected_value = corrected_value
        if correction_note is not None:
            field.correction_note = correction_note

        await self._db.flush()
        return field

    async def batch_update_status(
        self,
        field_ids: list[uuid.UUID],
        review_status: str,
        reviewer_id: uuid.UUID | None = None,
    ) -> int:
        """
        Bulk update review status for a list of field IDs.
        """
        if not field_ids:
            return 0

        now = datetime.now(timezone.utc)
        stmt = (
            update(ExtractedField)
            .where(ExtractedField.id.in_(field_ids))
            .values(
                review_status=review_status.upper(),
                corrected_by=reviewer_id,
                corrected_at=now,
            )
        )
        result = await self._db.execute(stmt)
        await self._db.flush()
        return result.rowcount

    async def get_review_summary(self, document_id: uuid.UUID) -> dict[str, Any]:
        """
        Calculates field count statistics and completion percentage for a document.
        """
        stmt = (
            select(
                ExtractedField.review_status,
                func.count(ExtractedField.id),
            )
            .join(DocumentExtraction, ExtractedField.extraction_id == DocumentExtraction.id)
            .where(DocumentExtraction.document_id == document_id)
            .group_by(ExtractedField.review_status)
        )
        result = await self._db.execute(stmt)
        counts = {row[0]: row[1] for row in result.all()}

        pending = counts.get(ReviewStatus.PENDING.value, 0)
        accepted = counts.get(ReviewStatus.ACCEPTED.value, 0)
        corrected = counts.get(ReviewStatus.CORRECTED.value, 0)
        rejected = counts.get(ReviewStatus.REJECTED.value, 0)
        total = pending + accepted + corrected + rejected

        reviewed = accepted + corrected + rejected
        completion_pct = round((reviewed / total * 100), 1) if total > 0 else 100.0

        return {
            "total_fields": total,
            "pending_count": pending,
            "accepted_count": accepted,
            "corrected_count": corrected,
            "rejected_count": rejected,
            "completion_pct": completion_pct,
            "is_complete": pending == 0 and total > 0,
        }

    async def record_audit_log(
        self,
        action: str,
        resource: str,
        user_id: uuid.UUID | None = None,
        resource_id: uuid.UUID | None = None,
        details: dict[str, Any] | None = None,
    ) -> AuditLog:
        """Create an immutable audit log entry."""
        log = AuditLog(
            user_id=user_id,
            action=action,
            resource=resource,
            resource_id=resource_id,
            details=details,
        )
        self._db.add(log)
        await self._db.flush()
        return log
