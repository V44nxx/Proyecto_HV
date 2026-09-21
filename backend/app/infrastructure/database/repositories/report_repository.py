"""
Report repository: data aggregation and extraction queries for institutional reports,
dynamic filtering, and audit trail logging.
"""

from datetime import datetime
from typing import Any
import uuid
import structlog
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.value_objects.report_types import (
    ReportColumn,
    ReportDataset,
    ReportType,
)
from app.infrastructure.database.models.document_models import (
    Document,
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
from app.infrastructure.database.models.user_models import AuditLog

logger = structlog.get_logger(__name__)


class ReportRepository:
    """Provides reporting data extraction methods and export audit logging."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_inventory_dataset(
        self,
        filters: dict[str, Any],
        generated_by: str,
        limit: int = 1000,
    ) -> ReportDataset:
        """Extracts dataset for Resume Inventory report."""
        stmt = (
            select(Document)
            .where(Document.deleted_at.is_(None))
            .options(
                selectinload(Document.person),
                selectinload(Document.processing_jobs),
            )
            .order_by(Document.created_at.desc())
        )

        # Filters
        if doc_type := filters.get("document_type"):
            stmt = stmt.where(Document.document_type == doc_type.upper())
        if start_date := filters.get("start_date"):
            stmt = stmt.where(Document.created_at >= start_date)
        if end_date := filters.get("end_date"):
            stmt = stmt.where(Document.created_at <= end_date)

        stmt = stmt.limit(limit)
        res = await self._db.execute(stmt)
        docs = res.scalars().all()

        columns = [
            ReportColumn("number", "N°", width_excel=8, width_pdf_ratio=0.5, align="center"),
            ReportColumn("filename", "Nombre de Archivo", width_excel=30, width_pdf_ratio=2.5),
            ReportColumn("document_type", "Formato", width_excel=16, width_pdf_ratio=1.2, align="center"),
            ReportColumn("candidate_name", "Candidato", width_excel=25, width_pdf_ratio=2.0),
            ReportColumn("identification", "Identificación", width_excel=18, width_pdf_ratio=1.2, align="center"),
            ReportColumn("status", "Estado", width_excel=16, width_pdf_ratio=1.2, align="center"),
            ReportColumn("size_kb", "Tamaño (KB)", width_excel=14, width_pdf_ratio=1.0, align="right"),
            ReportColumn("pages", "Páginas", width_excel=10, width_pdf_ratio=0.8, align="center"),
            ReportColumn("created_at", "Fecha de Carga", width_excel=20, width_pdf_ratio=1.5, align="center"),
        ]

        rows = []
        for idx, doc in enumerate(docs, start=1):
            cand_name = None
            ident = None
            if doc.person:
                parts = [doc.person.first_name, doc.person.first_surname]
                cand_name = " ".join(p for p in parts if p)
                ident = doc.person.identification_number

            job_status = "PENDING"
            if doc.processing_jobs:
                sorted_jobs = sorted(doc.processing_jobs, key=lambda j: j.created_at, reverse=True)
                job_status = sorted_jobs[0].status

            # Filter by status if requested
            if filter_status := filters.get("status"):
                if job_status != filter_status.upper():
                    continue

            rows.append({
                "number": idx,
                "filename": doc.original_filename,
                "document_type": doc.document_type or "UNKNOWN",
                "candidate_name": cand_name or "Sin vincular",
                "identification": ident or "—",
                "status": job_status,
                "size_kb": round(doc.file_size_bytes / 1024, 1),
                "pages": doc.page_count or 1,
                "created_at": doc.created_at,
            })

        return ReportDataset(
            report_type=ReportType.INVENTORY,
            title="Reporte de Inventario de Hojas de Vida",
            description="Registro detallado de documentos cargados en la plataforma, clasificación y estado de procesamiento.",
            generated_at=datetime.utcnow(),
            generated_by=generated_by,
            applied_filters=filters,
            columns=columns,
            rows=rows,
            total_records=len(rows),
        )

    async def get_classification_dataset(
        self,
        filters: dict[str, Any],
        generated_by: str,
        limit: int = 1000,
    ) -> ReportDataset:
        """Extracts dataset for Professional Classification report."""
        stmt = (
            select(Person)
            .where(Person.deleted_at.is_(None))
            .options(
                selectinload(Person.primary_category),
                selectinload(Person.primary_profession),
                selectinload(Person.experience_summary),
                selectinload(Person.educations),
                selectinload(Person.contact_information),
            )
            .order_by(Person.first_surname.asc(), Person.first_name.asc())
        )

        if cat_id := filters.get("category_id"):
            stmt = stmt.where(Person.primary_category_id == cat_id)
        if prof_id := filters.get("profession_id"):
            stmt = stmt.where(Person.primary_profession_id == prof_id)
        if start_date := filters.get("start_date"):
            stmt = stmt.where(Person.created_at >= start_date)
        if end_date := filters.get("end_date"):
            stmt = stmt.where(Person.created_at <= end_date)

        stmt = stmt.limit(limit)
        res = await self._db.execute(stmt)
        persons = res.scalars().all()

        columns = [
            ReportColumn("number", "N°", width_excel=8, width_pdf_ratio=0.5, align="center"),
            ReportColumn("candidate_name", "Candidato", width_excel=25, width_pdf_ratio=2.2),
            ReportColumn("identification", "Documento", width_excel=18, width_pdf_ratio=1.4, align="center"),
            ReportColumn("category", "Categoría Profesional", width_excel=26, width_pdf_ratio=2.0),
            ReportColumn("profession", "Profesión Canónica", width_excel=26, width_pdf_ratio=2.0),
            ReportColumn("academic_level", "Nivel Educativo", width_excel=18, width_pdf_ratio=1.4, align="center"),
            ReportColumn("experience_years", "Años Exp.", width_excel=12, width_pdf_ratio=0.9, align="right"),
            ReportColumn("location", "Ubicación", width_excel=22, width_pdf_ratio=1.6),
        ]

        rows = []
        for idx, p in enumerate(persons, start=1):
            parts = [p.first_name, p.middle_name, p.first_surname, p.second_surname]
            full_name = " ".join(part for part in parts if part)

            ident_str = f"{p.identification_type or ''} {p.identification_number or ''}".strip() or "—"
            cat_name = p.primary_category.name if p.primary_category else "Sin categoría"
            prof_name = p.primary_profession.name if p.primary_profession else "Sin clasificar"

            # Filter by profession name if provided
            if prof_filter := filters.get("profession_name"):
                if prof_filter.lower() not in prof_name.lower():
                    continue

            # Education level
            highest_level = "—"
            if p.educations:
                highest_level = p.educations[0].level

            # Experience
            exp_years = 0
            if p.experience_summary:
                exp_years = p.experience_summary.total_years

            if min_exp := filters.get("min_years_experience"):
                if exp_years < int(min_exp):
                    continue
            if max_exp := filters.get("max_years_experience"):
                if exp_years > int(max_exp):
                    continue

            # Location
            loc = "—"
            if p.contact_information:
                loc_parts = [p.contact_information.municipality, p.contact_information.department]
                loc = ", ".join(l for l in loc_parts if l) or "—"

            if dep_filter := filters.get("department"):
                if not p.contact_information or (p.contact_information.department or "").lower() != dep_filter.lower():
                    continue

            rows.append({
                "number": len(rows) + 1,
                "candidate_name": full_name or "Sin nombre",
                "identification": ident_str,
                "category": cat_name,
                "profession": prof_name,
                "academic_level": highest_level,
                "experience_years": exp_years,
                "location": loc,
            })

        return ReportDataset(
            report_type=ReportType.PROFESSIONAL_CLASSIFICATION,
            title="Reporte de Clasificación Profesional",
            description="Distribución y catalogación de candidatos por categorías y profesiones normalizadas.",
            generated_at=datetime.utcnow(),
            generated_by=generated_by,
            applied_filters=filters,
            columns=columns,
            rows=rows,
            total_records=len(rows),
        )

    async def get_academic_dataset(
        self,
        filters: dict[str, Any],
        generated_by: str,
        limit: int = 1000,
    ) -> ReportDataset:
        """Extracts dataset for Academic Formation report."""
        stmt = (
            select(Education)
            .join(Person, Education.person_id == Person.id)
            .where(Person.deleted_at.is_(None))
            .options(selectinload(Education.person))
            .order_by(Education.created_at.desc())
        )

        if level_filter := filters.get("academic_level"):
            stmt = stmt.where(Education.level == level_filter.upper())
        if institution_filter := filters.get("institution"):
            stmt = stmt.where(Education.institution.ilike(f"%{institution_filter}%"))
        if grad_status := filters.get("graduation_status"):
            stmt = stmt.where(Education.graduation_status == grad_status.upper())

        stmt = stmt.limit(limit)
        res = await self._db.execute(stmt)
        educations = res.scalars().all()

        columns = [
            ReportColumn("number", "N°", width_excel=8, width_pdf_ratio=0.5, align="center"),
            ReportColumn("candidate_name", "Candidato", width_excel=25, width_pdf_ratio=2.2),
            ReportColumn("identification", "Documento", width_excel=18, width_pdf_ratio=1.3, align="center"),
            ReportColumn("level", "Nivel Educativo", width_excel=18, width_pdf_ratio=1.4, align="center"),
            ReportColumn("degree_title", "Título Obtenido", width_excel=30, width_pdf_ratio=2.5),
            ReportColumn("institution", "Institución Educativa", width_excel=30, width_pdf_ratio=2.5),
            ReportColumn("graduation_status", "Estado", width_excel=16, width_pdf_ratio=1.2, align="center"),
            ReportColumn("professional_card", "Tarjeta Profesional", width_excel=20, width_pdf_ratio=1.4, align="center"),
        ]

        rows = []
        for idx, edu in enumerate(educations, start=1):
            cand_name = "—"
            ident = "—"
            if edu.person:
                parts = [edu.person.first_name, edu.person.first_surname]
                cand_name = " ".join(p for p in parts if p)
                ident = edu.person.identification_number or "—"

            rows.append({
                "number": idx,
                "candidate_name": cand_name,
                "identification": ident,
                "level": edu.level,
                "degree_title": edu.degree_title or "—",
                "institution": edu.institution or "—",
                "graduation_status": edu.graduation_status or "—",
                "professional_card": edu.professional_card_no or "—",
            })

        return ReportDataset(
            report_type=ReportType.ACADEMIC,
            title="Reporte de Formación Académica",
            description="Historial detallado de títulos, niveles formativos e instituciones educativas de los candidatos.",
            generated_at=datetime.utcnow(),
            generated_by=generated_by,
            applied_filters=filters,
            columns=columns,
            rows=rows,
            total_records=len(rows),
        )

    async def get_experience_dataset(
        self,
        filters: dict[str, Any],
        generated_by: str,
        limit: int = 1000,
    ) -> ReportDataset:
        """Extracts dataset for Work Experience report."""
        stmt = (
            select(Person)
            .where(Person.deleted_at.is_(None))
            .options(
                selectinload(Person.primary_profession),
                selectinload(Person.experience_summary),
                selectinload(Person.work_experiences),
            )
            .order_by(Person.first_surname.asc())
        )

        stmt = stmt.limit(limit)
        res = await self._db.execute(stmt)
        persons = res.scalars().all()

        columns = [
            ReportColumn("number", "N°", width_excel=8, width_pdf_ratio=0.5, align="center"),
            ReportColumn("candidate_name", "Candidato", width_excel=24, width_pdf_ratio=2.0),
            ReportColumn("identification", "Documento", width_excel=16, width_pdf_ratio=1.2, align="center"),
            ReportColumn("profession", "Profesión", width_excel=22, width_pdf_ratio=1.8),
            ReportColumn("total_years", "Total Años", width_excel=14, width_pdf_ratio=1.0, align="right"),
            ReportColumn("public_years", "Público", width_excel=12, width_pdf_ratio=0.9, align="right"),
            ReportColumn("private_years", "Privado", width_excel=12, width_pdf_ratio=0.9, align="right"),
            ReportColumn("independent_years", "Indep.", width_excel=12, width_pdf_ratio=0.9, align="right"),
            ReportColumn("last_position", "Último Cargo", width_excel=24, width_pdf_ratio=2.0),
            ReportColumn("last_company", "Última Empresa", width_excel=24, width_pdf_ratio=2.0),
        ]

        rows = []
        for p in persons:
            exp = p.experience_summary
            total_y = exp.total_years if exp else 0
            pub_y = exp.public_years if exp else 0
            priv_y = exp.private_years if exp else 0
            ind_y = exp.independent_years if exp else 0

            if min_exp := filters.get("min_years_experience"):
                if total_y < int(min_exp):
                    continue
            if max_exp := filters.get("max_years_experience"):
                if total_y > int(max_exp):
                    continue

            # Latest work experience
            last_pos = "—"
            last_comp = "—"
            if p.work_experiences:
                sorted_exp = sorted(
                    p.work_experiences,
                    key=lambda w: w.start_date or datetime.min,
                    reverse=True,
                )
                latest = sorted_exp[0]
                last_pos = latest.position or "—"
                last_comp = latest.company_name or "—"

            if company_filter := filters.get("company"):
                if company_filter.lower() not in last_comp.lower():
                    continue
            if position_filter := filters.get("position"):
                if position_filter.lower() not in last_pos.lower():
                    continue

            parts = [p.first_name, p.first_surname]
            full_name = " ".join(part for part in parts if part)
            prof_name = p.primary_profession.name if p.primary_profession else "Sin clasificar"

            rows.append({
                "number": len(rows) + 1,
                "candidate_name": full_name or "Sin nombre",
                "identification": p.identification_number or "—",
                "profession": prof_name,
                "total_years": total_y,
                "public_years": pub_y,
                "private_years": priv_y,
                "independent_years": ind_y,
                "last_position": last_pos,
                "last_company": last_comp,
            })

        return ReportDataset(
            report_type=ReportType.EXPERIENCE,
            title="Reporte de Trayectoria y Experiencia Laboral",
            description="Consolidado de años laborados por sector (público, privado e independiente) y cargos recientes.",
            generated_at=datetime.utcnow(),
            generated_by=generated_by,
            applied_filters=filters,
            columns=columns,
            rows=rows,
            total_records=len(rows),
        )

    async def get_geographic_dataset(
        self,
        filters: dict[str, Any],
        generated_by: str,
        limit: int = 1000,
    ) -> ReportDataset:
        """Extracts dataset for Geographic Distribution report."""
        stmt = (
            select(Person)
            .join(ContactInformation, ContactInformation.person_id == Person.id)
            .where(Person.deleted_at.is_(None))
            .options(
                selectinload(Person.contact_information),
                selectinload(Person.primary_profession),
                selectinload(Person.primary_category),
            )
            .order_by(ContactInformation.department.asc(), ContactInformation.municipality.asc())
        )

        if dep := filters.get("department"):
            stmt = stmt.where(ContactInformation.department == dep)
        if mun := filters.get("municipality"):
            stmt = stmt.where(ContactInformation.municipality == mun)

        stmt = stmt.limit(limit)
        res = await self._db.execute(stmt)
        persons = res.scalars().all()

        columns = [
            ReportColumn("number", "N°", width_excel=8, width_pdf_ratio=0.5, align="center"),
            ReportColumn("candidate_name", "Candidato", width_excel=25, width_pdf_ratio=2.2),
            ReportColumn("identification", "Documento", width_excel=18, width_pdf_ratio=1.4, align="center"),
            ReportColumn("department", "Departamento", width_excel=20, width_pdf_ratio=1.6),
            ReportColumn("municipality", "Municipio", width_excel=20, width_pdf_ratio=1.6),
            ReportColumn("email", "Correo Electrónico", width_excel=28, width_pdf_ratio=2.4),
            ReportColumn("phone", "Teléfono", width_excel=16, width_pdf_ratio=1.3, align="center"),
            ReportColumn("profession", "Profesión Principal", width_excel=24, width_pdf_ratio=2.0),
        ]

        rows = []
        for idx, p in enumerate(persons, start=1):
            parts = [p.first_name, p.first_surname]
            full_name = " ".join(part for part in parts if part)
            c = p.contact_information
            phone = c.mobile_phone or c.telephone or "—" if c else "—"
            email = c.email or "—" if c else "—"
            prof = p.primary_profession.name if p.primary_profession else "Sin clasificar"

            rows.append({
                "number": idx,
                "candidate_name": full_name or "Sin nombre",
                "identification": p.identification_number or "—",
                "department": c.department if c else "—",
                "municipality": c.municipality if c else "—",
                "email": email,
                "phone": phone,
                "profession": prof,
            })

        return ReportDataset(
            report_type=ReportType.GEOGRAPHIC,
            title="Reporte de Distribución Geográfica y Demográfica",
            description="Ubicación territorial de los candidatos por departamentos, municipios y datos de contacto.",
            generated_at=datetime.utcnow(),
            generated_by=generated_by,
            applied_filters=filters,
            columns=columns,
            rows=rows,
            total_records=len(rows),
        )

    async def get_custom_filtered_dataset(
        self,
        filters: dict[str, Any],
        generated_by: str,
        limit: int = 1000,
    ) -> ReportDataset:
        """Extracts dynamic dataset matching custom multi-criteria search parameters."""
        stmt = (
            select(Person)
            .where(Person.deleted_at.is_(None))
            .options(
                selectinload(Person.primary_category),
                selectinload(Person.primary_profession),
                selectinload(Person.contact_information),
                selectinload(Person.educations),
                selectinload(Person.experience_summary),
                selectinload(Person.documents),
            )
            .order_by(Person.first_surname.asc())
        )

        # Apply multi-criteria search filters
        if id_num := filters.get("identification_number"):
            stmt = stmt.where(Person.identification_number.ilike(f"%{id_num}%"))

        if name := filters.get("name"):
            name_pat = f"%{name}%"
            stmt = stmt.where(
                or_(
                    Person.first_name.ilike(name_pat),
                    Person.first_surname.ilike(name_pat),
                    Person.second_surname.ilike(name_pat),
                )
            )

        if cat_id := filters.get("category_id"):
            stmt = stmt.where(Person.primary_category_id == cat_id)

        if prof_id := filters.get("profession_id"):
            stmt = stmt.where(Person.primary_profession_id == prof_id)

        if dep := filters.get("department"):
            stmt = stmt.where(
                Person.contact_information.has(ContactInformation.department == dep)
            )

        if mun := filters.get("municipality"):
            stmt = stmt.where(
                Person.contact_information.has(ContactInformation.municipality == mun)
            )

        if acad_lvl := filters.get("academic_level"):
            stmt = stmt.where(
                Person.educations.any(Education.level == acad_lvl.upper())
            )

        stmt = stmt.limit(limit)
        res = await self._db.execute(stmt)
        persons = res.scalars().all()

        columns = [
            ReportColumn("number", "N°", width_excel=8, width_pdf_ratio=0.5, align="center"),
            ReportColumn("candidate_name", "Candidato", width_excel=25, width_pdf_ratio=2.2),
            ReportColumn("identification", "Documento", width_excel=18, width_pdf_ratio=1.4, align="center"),
            ReportColumn("category", "Categoría", width_excel=24, width_pdf_ratio=1.8),
            ReportColumn("profession", "Profesión", width_excel=24, width_pdf_ratio=1.8),
            ReportColumn("academic_level", "Nivel", width_excel=16, width_pdf_ratio=1.2, align="center"),
            ReportColumn("experience_years", "Años Exp.", width_excel=12, width_pdf_ratio=0.9, align="right"),
            ReportColumn("location", "Ubicación", width_excel=22, width_pdf_ratio=1.6),
            ReportColumn("email", "Correo", width_excel=26, width_pdf_ratio=2.0),
        ]

        rows = []
        for p in persons:
            parts = [p.first_name, p.first_surname]
            full_name = " ".join(part for part in parts if part)
            cat = p.primary_category.name if p.primary_category else "—"
            prof = p.primary_profession.name if p.primary_profession else "—"
            lvl = p.educations[0].level if p.educations else "—"
            exp_y = p.experience_summary.total_years if p.experience_summary else 0
            email = p.contact_information.email if p.contact_information else "—"

            loc = "—"
            if p.contact_information:
                loc_parts = [p.contact_information.municipality, p.contact_information.department]
                loc = ", ".join(l for l in loc_parts if l) or "—"

            if min_exp := filters.get("min_years_experience"):
                if exp_y < int(min_exp):
                    continue
            if max_exp := filters.get("max_years_experience"):
                if exp_y > int(max_exp):
                    continue

            rows.append({
                "number": len(rows) + 1,
                "candidate_name": full_name or "Sin nombre",
                "identification": p.identification_number or "—",
                "category": cat,
                "profession": prof,
                "academic_level": lvl,
                "experience_years": exp_y,
                "location": loc,
                "email": email,
            })

        return ReportDataset(
            report_type=ReportType.CUSTOM_FILTERED,
            title="Reporte de Búsqueda Personalizada Multicriterio",
            description="Exportación dinámica de candidatos que cumplen con los criterios específicos de búsqueda institucional.",
            generated_at=datetime.utcnow(),
            generated_by=generated_by,
            applied_filters=filters,
            columns=columns,
            rows=rows,
            total_records=len(rows),
        )

    async def record_audit_log(
        self,
        user_id: uuid.UUID | None,
        action: str,
        resource: str | None = None,
        resource_id: uuid.UUID | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> AuditLog:
        """Records an immutable audit log entry for report export actions."""
        log_entry = AuditLog(
            id=uuid.uuid4(),
            user_id=user_id,
            action=action,
            resource=resource,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details,
        )
        self._db.add(log_entry)
        await self._db.flush()
        return log_entry
