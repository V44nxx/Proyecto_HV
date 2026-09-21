"""
Search repository: multi-criteria querying, pagination, candidate dossier loading,
aggregation facets, and taxonomy management.
"""

from datetime import datetime
from typing import Any
import uuid
import structlog
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.services.profession_classifier import TAXONOMY
from app.infrastructure.database.models.document_models import Document
from app.infrastructure.database.models.person_models import (
    ContactInformation,
    Person,
    Profession,
    ProfessionalCategory,
)
from app.infrastructure.database.models.resume_models import (
    Certification,
    Education,
    ExperienceSummary,
    Language,
    ProfessionalProfile,
    WorkExperience,
)

logger = structlog.get_logger(__name__)


class SearchRepository:
    """Handles advanced searching, filtering, and aggregation queries for candidates."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def seed_default_taxonomy(self) -> int:
        """
        Seeds canonical professional categories and professions idempotently.
        Returns the number of created professions.
        """
        created_count = 0
        for cat_name, professions in TAXONOMY.items():
            cat_stmt = select(ProfessionalCategory).where(ProfessionalCategory.name == cat_name)
            cat_res = await self._db.execute(cat_stmt)
            category = cat_res.scalar_one_or_none()

            if not category:
                category = ProfessionalCategory(name=cat_name, description=f"Sector de {cat_name}")
                self._db.add(category)
                await self._db.flush()

            for prof_data in professions:
                prof_name = prof_data["profession"]
                aliases = prof_data.get("aliases", [])

                prof_stmt = select(Profession).where(Profession.name == prof_name)
                prof_res = await self._db.execute(prof_stmt)
                existing_prof = prof_res.scalar_one_or_none()

                if not existing_prof:
                    new_prof = Profession(
                        category_id=category.id,
                        name=prof_name,
                        aliases=aliases,
                        is_active=True,
                    )
                    self._db.add(new_prof)
                    created_count += 1

        await self._db.flush()
        return created_count

    async def list_categories_with_professions(self) -> list[ProfessionalCategory]:
        """Fetch all categories with eager-loaded professions."""
        stmt = (
            select(ProfessionalCategory)
            .where(ProfessionalCategory.is_active.is_(True))
            .options(selectinload(ProfessionalCategory.professions))
            .order_by(ProfessionalCategory.name.asc())
        )
        res = await self._db.execute(stmt)
        return list(res.scalars().all())

    async def get_candidate_detail(self, person_id: uuid.UUID) -> Person | None:
        """Fetch a single person with complete relational history."""
        stmt = (
            select(Person)
            .where(Person.id == person_id, Person.deleted_at.is_(None))
            .options(
                selectinload(Person.contact_information),
                selectinload(Person.primary_profession),
                selectinload(Person.educations),
                selectinload(Person.work_experiences),
                selectinload(Person.experience_summary),
                selectinload(Person.languages),
                selectinload(Person.certifications),
                selectinload(Person.professional_profile),
                selectinload(Person.documents),
            )
        )
        res = await self._db.execute(stmt)
        return res.scalar_one_or_none()

    async def search_candidates(
        self,
        filters: dict[str, Any],
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[Person], int]:
        """
        Executes multi-criteria candidate search with server-side pagination and sorting.
        """
        base_stmt = select(Person).where(Person.deleted_at.is_(None))
        count_stmt = select(func.count(Person.id)).where(Person.deleted_at.is_(None))

        conditions = []

        # 1. Full text query (q)
        q = filters.get("q")
        if q and q.strip():
            pattern = f"%{q.strip()}%"
            full_name = func.concat(
                func.coalesce(Person.first_name, ""), " ",
                func.coalesce(Person.middle_name, ""), " ",
                func.coalesce(Person.first_surname, ""), " ",
                func.coalesce(Person.second_surname, ""),
            )
            q_conditions = [
                full_name.ilike(pattern),
                Person.identification_number.ilike(pattern),
                Person.contact_information.has(ContactInformation.email.ilike(pattern)),
                Person.contact_information.has(ContactInformation.telephone.ilike(pattern)),
                Person.contact_information.has(ContactInformation.municipality.ilike(pattern)),
                Person.contact_information.has(ContactInformation.department.ilike(pattern)),
                Person.educations.any(Education.degree_title.ilike(pattern)),
                Person.educations.any(Education.institution.ilike(pattern)),
                Person.work_experiences.any(WorkExperience.company_name.ilike(pattern)),
                Person.work_experiences.any(WorkExperience.position.ilike(pattern)),
                Person.professional_profile.has(ProfessionalProfile.summary.ilike(pattern)),
            ]
            conditions.append(or_(*q_conditions))

        # 2. Specific filters
        if filters.get("identification_number"):
            id_pat = f"%{filters['identification_number'].strip()}%"
            conditions.append(Person.identification_number.ilike(id_pat))

        if filters.get("name"):
            name_pat = f"%{filters['name'].strip()}%"
            full_name = func.concat(
                func.coalesce(Person.first_name, ""), " ",
                func.coalesce(Person.middle_name, ""), " ",
                func.coalesce(Person.first_surname, ""), " ",
                func.coalesce(Person.second_surname, ""),
            )
            conditions.append(full_name.ilike(name_pat))

        if filters.get("category_id"):
            conditions.append(Person.primary_category_id == filters["category_id"])

        if filters.get("profession_id"):
            conditions.append(Person.primary_profession_id == filters["profession_id"])

        if filters.get("profession_name"):
            prof_pat = f"%{filters['profession_name'].strip()}%"
            conditions.append(
                Person.primary_profession.has(Profession.name.ilike(prof_pat))
            )

        if filters.get("academic_level"):
            conditions.append(
                Person.educations.any(Education.level == filters["academic_level"].upper())
            )

        if filters.get("institution"):
            inst_pat = f"%{filters['institution'].strip()}%"
            conditions.append(Person.educations.any(Education.institution.ilike(inst_pat)))

        if filters.get("company"):
            comp_pat = f"%{filters['company'].strip()}%"
            conditions.append(Person.work_experiences.any(WorkExperience.company_name.ilike(comp_pat)))

        if filters.get("position"):
            pos_pat = f"%{filters['position'].strip()}%"
            conditions.append(Person.work_experiences.any(WorkExperience.position.ilike(pos_pat)))

        if filters.get("department"):
            dep_pat = f"%{filters['department'].strip()}%"
            conditions.append(Person.contact_information.has(ContactInformation.department.ilike(dep_pat)))

        if filters.get("municipality"):
            mun_pat = f"%{filters['municipality'].strip()}%"
            conditions.append(Person.contact_information.has(ContactInformation.municipality.ilike(mun_pat)))

        if filters.get("min_years_experience") is not None:
            conditions.append(
                Person.experience_summary.has(
                    ExperienceSummary.total_years >= filters["min_years_experience"]
                )
            )

        if filters.get("max_years_experience") is not None:
            conditions.append(
                Person.experience_summary.has(
                    ExperienceSummary.total_years <= filters["max_years_experience"]
                )
            )

        if filters.get("language"):
            lang_pat = f"%{filters['language'].strip()}%"
            conditions.append(Person.languages.any(Language.language_name.ilike(lang_pat)))

        if filters.get("skills"):
            skill_pat = f"%{filters['skills'].strip()}%"
            conditions.append(
                Person.professional_profile.has(ProfessionalProfile.summary.ilike(skill_pat))
            )

        if filters.get("certification"):
            cert_pat = f"%{filters['certification'].strip()}%"
            conditions.append(Person.certifications.any(Certification.name.ilike(cert_pat)))

        if filters.get("document_type"):
            conditions.append(
                Person.documents.any(Document.document_type == filters["document_type"].upper())
            )

        if filters.get("created_from"):
            conditions.append(Person.created_at >= filters["created_from"])

        if filters.get("created_to"):
            conditions.append(Person.created_at <= filters["created_to"])

        # Apply conditions to both queries
        for cond in conditions:
            base_stmt = base_stmt.where(cond)
            count_stmt = count_stmt.where(cond)

        # Count total
        total_res = await self._db.execute(count_stmt)
        total = total_res.scalar() or 0

        # Sorting
        if sort_by == "name":
            sort_expr = Person.first_surname.desc() if sort_order.lower() == "desc" else Person.first_surname.asc()
        elif sort_by == "experience":
            # Sort fallback
            sort_expr = Person.created_at.desc() if sort_order.lower() == "desc" else Person.created_at.asc()
        else:
            sort_expr = Person.created_at.desc() if sort_order.lower() == "desc" else Person.created_at.asc()

        base_stmt = (
            base_stmt.order_by(sort_expr)
            .offset((page - 1) * page_size)
            .limit(page_size)
            .options(
                selectinload(Person.contact_information),
                selectinload(Person.primary_profession),
                selectinload(Person.primary_category),
                selectinload(Person.educations),
                selectinload(Person.work_experiences),
                selectinload(Person.experience_summary),
                selectinload(Person.languages),
                selectinload(Person.certifications),
                selectinload(Person.professional_profile),
                selectinload(Person.documents),
            )
        )

        candidates_res = await self._db.execute(base_stmt)
        candidates = list(candidates_res.scalars().all())

        return candidates, total

    async def get_search_facets(self) -> dict[str, Any]:
        """
        Computes aggregated facet statistics across all active candidates.
        """
        # 1. Total Candidates
        total_stmt = select(func.count(Person.id)).where(Person.deleted_at.is_(None))
        total_candidates = (await self._db.execute(total_stmt)).scalar() or 0

        # 2. Count by Academic Level
        level_stmt = (
            select(Education.level, func.count(Education.id))
            .join(Person, Education.person_id == Person.id)
            .where(Person.deleted_at.is_(None))
            .group_by(Education.level)
        )
        level_res = await self._db.execute(level_stmt)
        by_level = {row[0]: row[1] for row in level_res.all()}

        # 3. Count by Department
        dep_stmt = (
            select(ContactInformation.department, func.count(ContactInformation.id))
            .join(Person, ContactInformation.person_id == Person.id)
            .where(Person.deleted_at.is_(None), ContactInformation.department.is_not(None))
            .group_by(ContactInformation.department)
            .order_by(func.count(ContactInformation.id).desc())
            .limit(10)
        )
        dep_res = await self._db.execute(dep_stmt)
        by_department = {row[0]: row[1] for row in dep_res.all() if row[0]}

        # 4. Count by Top Professions
        prof_stmt = (
            select(Profession.name, func.count(Person.id))
            .join(Person, Person.primary_profession_id == Profession.id)
            .where(Person.deleted_at.is_(None))
            .group_by(Profession.name)
            .order_by(func.count(Person.id).desc())
            .limit(10)
        )
        prof_res = await self._db.execute(prof_stmt)
        by_profession = {row[0]: row[1] for row in prof_res.all()}

        # 5. Count by Top Categories
        cat_stmt = (
            select(ProfessionalCategory.name, func.count(Person.id))
            .join(Person, Person.primary_category_id == ProfessionalCategory.id)
            .where(Person.deleted_at.is_(None))
            .group_by(ProfessionalCategory.name)
            .order_by(func.count(Person.id).desc())
        )
        cat_res = await self._db.execute(cat_stmt)
        by_category = {row[0]: row[1] for row in cat_res.all()}

        return {
            "total_candidates": total_candidates,
            "by_category": by_category,
            "by_profession": by_profession,
            "by_academic_level": by_level,
            "by_department": by_department,
        }
