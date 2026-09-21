"""
Use case to list all available institutional reports and their specifications.
"""

from dataclasses import dataclass
from typing import Any
from app.domain.value_objects.report_types import ReportFormat, ReportType


@dataclass(frozen=True)
class AvailableReportInfo:
    """Catalog entry describing a downloadable institutional report."""
    report_type: ReportType
    title: str
    description: str
    supported_formats: list[ReportFormat]
    filter_fields: list[str]


class ListAvailableReportsUseCase:
    """Provides the institutional report catalog."""

    def execute(self) -> list[AvailableReportInfo]:
        """Returns the list of available reports with metadata and filters."""
        return [
            AvailableReportInfo(
                report_type=ReportType.INVENTORY,
                title="Inventario de Hojas de Vida",
                description="Registro exhaustivo de documentos cargados, clasificación (Formato Único DAFP / ATS), estado de procesamiento, tamaño y fechas de carga.",
                supported_formats=[ReportFormat.EXCEL, ReportFormat.PDF],
                filter_fields=["document_type", "status", "start_date", "end_date"],
            ),
            AvailableReportInfo(
                report_type=ReportType.PROFESSIONAL_CLASSIFICATION,
                title="Clasificación Profesional",
                description="Listado de candidatos agrupados por categorías profesionales, profesiones canónicas normalizadas, años de experiencia y ubicación.",
                supported_formats=[ReportFormat.EXCEL, ReportFormat.PDF],
                filter_fields=["category_id", "profession_name", "department", "min_years_experience", "max_years_experience"],
            ),
            AvailableReportInfo(
                report_type=ReportType.ACADEMIC,
                title="Formación Académica",
                description="Desglose detallado de estudios, títulos académicos obtenidos, instituciones educativas, niveles formativos y tarjetas profesionales.",
                supported_formats=[ReportFormat.EXCEL, ReportFormat.PDF],
                filter_fields=["academic_level", "institution", "graduation_status"],
            ),
            AvailableReportInfo(
                report_type=ReportType.EXPERIENCE,
                title="Trayectoria Laboral y Experiencia",
                description="Consolidado de trayectoria profesional, discriminando años en el sector público, privado e independiente, y cargos desempeñados.",
                supported_formats=[ReportFormat.EXCEL, ReportFormat.PDF],
                filter_fields=["min_years_experience", "max_years_experience", "company", "position"],
            ),
            AvailableReportInfo(
                report_type=ReportType.GEOGRAPHIC,
                title="Distribución Geográfica y Demográfica",
                description="Ubicación territorial de los candidatos por departamentos y municipios colombianos con datos de contacto institucional.",
                supported_formats=[ReportFormat.EXCEL, ReportFormat.PDF],
                filter_fields=["department", "municipality"],
            ),
            AvailableReportInfo(
                report_type=ReportType.CUSTOM_FILTERED,
                title="Búsqueda Personalizada Multicriterio",
                description="Exportación dinámica que responde a los parámetros avanzados de búsqueda seleccionados por el usuario en tiempo real.",
                supported_formats=[ReportFormat.EXCEL, ReportFormat.PDF],
                filter_fields=["q", "identification_number", "name", "category_id", "profession_id", "academic_level", "department", "municipality", "min_years_experience"],
            ),
        ]
