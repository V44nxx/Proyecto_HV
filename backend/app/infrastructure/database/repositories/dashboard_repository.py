"""
Dashboard repository: aggregated queries, institutional KPIs, format distributions,
demographic metrics, pending review queues, and recent activity feeds.
"""

from typing import Any
import uuid
import structlog
from sqlalchemy import case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config.constants import JobStatus, ReviewStatus
from app.infrastructure.database.models.document_models import (
    Document,
    DocumentExtraction,
    ExtractedField,
    ProcessingJob,
)
from app.infrastructure.database.models.person_models import (
    ContactInformation,
    Person,
    Profession,
    ProfessionalCategory,
)
from app.infrastructure.database.models.resume_models import (
    Education,
    ExperienceSummary,
    WorkExperience,
)

logger = structlog.get_logger(__name__)


class DashboardRepository:
    """Handles real-time metric aggregation queries for the institutional dashboard."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_kpis(self) -> dict[str, Any]:
        """Calculates core executive and operational metrics."""
        # 1. Total active resumes
        total_docs_stmt = select(func.count(Document.id)).where(Document.deleted_at.is_(None))
        total_docs = (await self._db.execute(total_docs_stmt)).scalar() or 0

        # 2. Total active persons
        total_persons_stmt = select(func.count(Person.id)).where(Person.deleted_at.is_(None))
        total_persons = (await self._db.execute(total_persons_stmt)).scalar() or 0

        # 3. Classified professionals
        total_profs_stmt = select(func.count(Person.id)).where(
            Person.deleted_at.is_(None),
            Person.primary_profession_id.is_not(None),
        )
        total_professionals = (await self._db.execute(total_profs_stmt)).scalar() or 0

        # 4. Successfully processed resumes
        proc_stmt = (
            select(func.count(func.distinct(ProcessingJob.document_id)))
            .join(Document, Document.id == ProcessingJob.document_id)
            .where(
                Document.deleted_at.is_(None),
                ProcessingJob.status == JobStatus.COMPLETED.value,
            )
        )
        processed_docs = (await self._db.execute(proc_stmt)).scalar() or 0

        # 5. Documents requiring review
        review_stmt = (
            select(func.count(func.distinct(ProcessingJob.document_id)))
            .join(Document, Document.id == ProcessingJob.document_id)
            .where(
                Document.deleted_at.is_(None),
                or_(
                    ProcessingJob.status == JobStatus.REVIEW_REQUIRED.value,
                    ProcessingJob.current_step == "review_required",
                ),
            )
        )
        requiring_review = (await self._db.execute(review_stmt)).scalar() or 0

        # 6. Success rate
        success_rate = (
            round(min(100.0, (processed_docs / total_docs * 100)), 1)
            if total_docs > 0
            else 100.0
        )

        return {
            "total_documents": total_docs,
            "total_persons": total_persons,
            "total_professionals": total_professionals,
            "processed_documents": processed_docs,
            "documents_requiring_review": requiring_review,
            "extraction_success_rate": success_rate,
        }

    async def get_format_distribution(self) -> list[dict[str, Any]]:
        """Distribution of documents by classification type."""
        stmt = (
            select(
                Document.document_type,
                func.count(Document.id),
            )
            .where(Document.deleted_at.is_(None))
            .group_by(Document.document_type)
        )
        res = await self._db.execute(stmt)
        rows = res.all()
        total = sum(r[1] for r in rows) or 1

        items = []
        for dtype, count in rows:
            label = dtype or "UNKNOWN"
            items.append({
                "label": label,
                "count": count,
                "percentage": round(count / total * 100, 1),
            })
        return items

    async def get_category_distribution(self) -> list[dict[str, Any]]:
        """Distribution of candidates across professional categories."""
        stmt = (
            select(
                ProfessionalCategory.name,
                func.count(Person.id),
            )
            .join(Person, Person.primary_category_id == ProfessionalCategory.id)
            .where(Person.deleted_at.is_(None))
            .group_by(ProfessionalCategory.name)
            .order_by(func.count(Person.id).desc())
        )
        res = await self._db.execute(stmt)
        rows = res.all()
        total = sum(r[1] for r in rows) or 1

        items = []
        for cat_name, count in rows:
            items.append({
                "label": cat_name,
                "count": count,
                "percentage": round(count / total * 100, 1),
            })
        return items

    async def get_top_professions(self, limit: int = 10) -> list[dict[str, Any]]:
        """Top normalized professions with candidate counts."""
        stmt = (
            select(
                Profession.name,
                func.count(Person.id),
            )
            .join(Person, Person.primary_profession_id == Profession.id)
            .where(Person.deleted_at.is_(None))
            .group_by(Profession.name)
            .order_by(func.count(Person.id).desc())
            .limit(limit)
        )
        res = await self._db.execute(stmt)
        rows = res.all()
        total = sum(r[1] for r in rows) or 1

        items = []
        for prof_name, count in rows:
            items.append({
                "label": prof_name,
                "count": count,
                "percentage": round(count / total * 100, 1),
            })
        return items

    async def get_academic_level_distribution(self) -> list[dict[str, Any]]:
        """Distribution by highest or consolidated education levels."""
        stmt = (
            select(
                Education.level,
                func.count(Education.id),
            )
            .join(Person, Education.person_id == Person.id)
            .where(Person.deleted_at.is_(None))
            .group_by(Education.level)
            .order_by(func.count(Education.id).desc())
        )
        res = await self._db.execute(stmt)
        rows = res.all()
        total = sum(r[1] for r in rows) or 1

        items = []
        for lvl, count in rows:
            items.append({
                "label": lvl,
                "count": count,
                "percentage": round(count / total * 100, 1),
            })
        return items

    async def get_experience_distribution(self) -> dict[str, int]:
        """Distribution of candidate experience grouped into standard brackets."""
        stmt = select(
            func.count(case((ExperienceSummary.total_years <= 2, 1))),
            func.count(case(((ExperienceSummary.total_years >= 3) & (ExperienceSummary.total_years <= 5), 1))),
            func.count(case(((ExperienceSummary.total_years >= 6) & (ExperienceSummary.total_years <= 10), 1))),
            func.count(case((ExperienceSummary.total_years > 10, 1))),
        ).join(Person, ExperienceSummary.person_id == Person.id).where(Person.deleted_at.is_(None))

        res = await self._db.execute(stmt)
        row = res.one_or_none()
        if row:
            return {
                "0_to_2_years": row[0] or 0,
                "3_to_5_years": row[1] or 0,
                "6_to_10_years": row[2] or 0,
                "more_than_10_years": row[3] or 0,
            }
        return {
            "0_to_2_years": 0,
            "3_to_5_years": 0,
            "6_to_10_years": 0,
            "more_than_10_years": 0,
        }

    async def get_geographic_distribution(self, limit: int = 10) -> list[dict[str, Any]]:
        """Top geographic departments with candidate counts."""
        stmt = (
            select(
                ContactInformation.department,
                func.count(ContactInformation.id),
            )
            .join(Person, ContactInformation.person_id == Person.id)
            .where(
                Person.deleted_at.is_(None),
                ContactInformation.department.is_not(None),
            )
            .group_by(ContactInformation.department)
            .order_by(func.count(ContactInformation.id).desc())
            .limit(limit)
        )
        res = await self._db.execute(stmt)
        rows = res.all()
        total = sum(r[1] for r in rows) or 1

        items = []
        for dep, count in rows:
            if dep:
                items.append({
                    "label": dep,
                    "count": count,
                    "percentage": round(count / total * 100, 1),
                })
        return items

    async def get_documents_requiring_review(self, limit: int = 10) -> list[dict[str, Any]]:
        """List of documents requiring human validation attention."""
        # Find documents where latest processing job is REVIEW_REQUIRED or has pending fields
        stmt = (
            select(Document, ProcessingJob)
            .join(ProcessingJob, ProcessingJob.document_id == Document.id)
            .where(
                Document.deleted_at.is_(None),
                or_(
                    ProcessingJob.status == JobStatus.REVIEW_REQUIRED.value,
                    ProcessingJob.current_step == "review_required",
                ),
            )
            .order_by(Document.created_at.desc())
            .limit(limit)
        )
        res = await self._db.execute(stmt)
        rows = res.all()

        items = []
        seen_doc_ids: set[uuid.UUID] = set()
        for doc, job in rows:
            if doc.id in seen_doc_ids:
                continue
            seen_doc_ids.add(doc.id)
            items.append({
                "document_id": doc.id,
                "filename": doc.original_filename,
                "document_type": doc.document_type or "UNKNOWN",
                "job_id": job.id,
                "current_step": job.current_step,
                "error_message": job.error_message,
                "created_at": doc.created_at,
            })
            if len(items) >= limit:
                break
        return items

    async def get_recent_activity(self, limit: int = 10) -> list[dict[str, Any]]:
        """Recent document uploads and their processing outcomes."""
        stmt = (
            select(Document)
            .where(Document.deleted_at.is_(None))
            .options(
                selectinload(Document.person),
                selectinload(Document.processing_jobs),
            )
            .order_by(Document.created_at.desc())
            .limit(limit)
        )
        res = await self._db.execute(stmt)
        docs = res.scalars().all()

        items = []
        for d in docs:
            # Candidate full name
            candidate_name = None
            if d.person:
                parts = [d.person.first_name, d.person.first_surname]
                candidate_name = " ".join(p for p in parts if p)

            # Latest job status
            job_status = "UNKNOWN"
            if d.processing_jobs:
                sorted_jobs = sorted(d.processing_jobs, key=lambda j: j.created_at, reverse=True)
                job_status = sorted_jobs[0].status

            items.append({
                "document_id": d.id,
                "filename": d.original_filename,
                "document_type": d.document_type or "UNKNOWN",
                "candidate_name": candidate_name,
                "person_id": d.person_id,
                "status": job_status,
                "file_size_bytes": d.file_size_bytes,
                "created_at": d.created_at,
            })
        return items
