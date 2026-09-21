"""
Use case to generate a lightweight data preview of an institutional report.
"""

from typing import Any
import structlog

from app.domain.value_objects.report_types import ReportDataset, ReportType
from app.infrastructure.database.repositories.report_repository import ReportRepository

logger = structlog.get_logger(__name__)


class GetReportPreviewUseCase:
    """Provides a sample slice of report rows and column headers before full export."""

    def __init__(self, report_repo: ReportRepository) -> None:
        self._report_repo = report_repo

    async def execute(
        self,
        report_type: ReportType,
        filters: dict[str, Any],
        generated_by: str,
        preview_limit: int = 20,
    ) -> ReportDataset:
        """Queries the first N records matching filters for the specified report type."""
        if report_type == ReportType.INVENTORY:
            return await self._report_repo.get_inventory_dataset(
                filters=filters,
                generated_by=generated_by,
                limit=preview_limit,
            )
        elif report_type == ReportType.PROFESSIONAL_CLASSIFICATION:
            return await self._report_repo.get_classification_dataset(
                filters=filters,
                generated_by=generated_by,
                limit=preview_limit,
            )
        elif report_type == ReportType.ACADEMIC:
            return await self._report_repo.get_academic_dataset(
                filters=filters,
                generated_by=generated_by,
                limit=preview_limit,
            )
        elif report_type == ReportType.EXPERIENCE:
            return await self._report_repo.get_experience_dataset(
                filters=filters,
                generated_by=generated_by,
                limit=preview_limit,
            )
        elif report_type == ReportType.GEOGRAPHIC:
            return await self._report_repo.get_geographic_dataset(
                filters=filters,
                generated_by=generated_by,
                limit=preview_limit,
            )
        elif report_type == ReportType.CUSTOM_FILTERED:
            return await self._report_repo.get_custom_filtered_dataset(
                filters=filters,
                generated_by=generated_by,
                limit=preview_limit,
            )
        else:
            raise ValueError(f"Tipo de reporte no soportado: {report_type}")
