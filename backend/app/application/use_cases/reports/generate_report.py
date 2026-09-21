"""
Use case to generate, format, and audit an institutional report export.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any
import uuid
import structlog

from app.domain.value_objects.report_types import (
    ReportDataset,
    ReportFormat,
    ReportType,
)
from app.infrastructure.database.repositories.report_repository import ReportRepository
from app.infrastructure.reporting.excel_report_generator import ExcelReportGenerator
from app.infrastructure.reporting.pdf_report_generator import PdfReportGenerator

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class GeneratedReportResult:
    """Outcome of a successful report export."""
    filename: str
    media_type: str
    content: bytes
    total_records: int


class GenerateReportUseCase:
    """Orchestrates report dataset retrieval, document rendering, and audit trail logging."""

    MIME_TYPES = {
        ReportFormat.EXCEL: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ReportFormat.PDF: "application/pdf",
    }

    EXTENSIONS = {
        ReportFormat.EXCEL: "xlsx",
        ReportFormat.PDF: "pdf",
    }

    FILE_PREFIXES = {
        ReportType.INVENTORY: "reporte_inventario",
        ReportType.PROFESSIONAL_CLASSIFICATION: "reporte_clasificacion_profesional",
        ReportType.ACADEMIC: "reporte_formacion_academica",
        ReportType.EXPERIENCE: "reporte_experiencia_laboral",
        ReportType.GEOGRAPHIC: "reporte_distribucion_geografica",
        ReportType.CUSTOM_FILTERED: "reporte_busqueda_filtrada",
    }

    def __init__(
        self,
        report_repo: ReportRepository,
        excel_gen: ExcelReportGenerator | None = None,
        pdf_gen: PdfReportGenerator | None = None,
    ) -> None:
        self._report_repo = report_repo
        self._excel_gen = excel_gen or ExcelReportGenerator()
        self._pdf_gen = pdf_gen or PdfReportGenerator()

    async def execute(
        self,
        report_type: ReportType,
        report_format: ReportFormat,
        filters: dict[str, Any],
        user_id: uuid.UUID | None,
        user_name: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
        limit: int = 5000,
    ) -> GeneratedReportResult:
        """Generates document bytes, records audit trail, and returns file download details."""
        # 1. Fetch Dataset
        dataset = await self._fetch_dataset(report_type, filters, user_name, limit)

        # 2. Render Binary Document
        if report_format == ReportFormat.EXCEL:
            content = self._excel_gen.generate(dataset)
        elif report_format == ReportFormat.PDF:
            content = self._pdf_gen.generate(dataset)
        else:
            raise ValueError(f"Formato no soportado: {report_format}")

        # 3. Generate sanitized institutional filename
        timestamp_str = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        prefix = self.FILE_PREFIXES.get(report_type, "reporte_institucional")
        ext = self.EXTENSIONS[report_format]
        filename = f"{prefix}_{timestamp_str}.{ext}"
        media_type = self.MIME_TYPES[report_format]

        # 4. Audit Trail Logging (Chapter 22 requirement)
        await self._report_repo.record_audit_log(
            user_id=user_id,
            action="EXPORT_REPORT",
            resource="reports",
            ip_address=ip_address,
            user_agent=user_agent,
            details={
                "report_type": report_type.value,
                "format": report_format.value,
                "filename": filename,
                "total_records": dataset.total_records,
                "filters": filters,
            },
        )

        logger.info(
            "report_exported_successfully",
            report_type=report_type.value,
            format=report_format.value,
            records=dataset.total_records,
            filename=filename,
            user_id=str(user_id) if user_id else None,
        )

        return GeneratedReportResult(
            filename=filename,
            media_type=media_type,
            content=content,
            total_records=dataset.total_records,
        )

    async def _fetch_dataset(
        self,
        report_type: ReportType,
        filters: dict[str, Any],
        user_name: str,
        limit: int,
    ) -> ReportDataset:
        if report_type == ReportType.INVENTORY:
            return await self._report_repo.get_inventory_dataset(filters, user_name, limit)
        elif report_type == ReportType.PROFESSIONAL_CLASSIFICATION:
            return await self._report_repo.get_classification_dataset(filters, user_name, limit)
        elif report_type == ReportType.ACADEMIC:
            return await self._report_repo.get_academic_dataset(filters, user_name, limit)
        elif report_type == ReportType.EXPERIENCE:
            return await self._report_repo.get_experience_dataset(filters, user_name, limit)
        elif report_type == ReportType.GEOGRAPHIC:
            return await self._report_repo.get_geographic_dataset(filters, user_name, limit)
        elif report_type == ReportType.CUSTOM_FILTERED:
            return await self._report_repo.get_custom_filtered_dataset(filters, user_name, limit)
        else:
            raise ValueError(f"Tipo de reporte no soportado: {report_type}")
