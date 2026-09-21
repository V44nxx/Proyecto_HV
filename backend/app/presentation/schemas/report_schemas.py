"""
Pydantic v2 schemas for Report catalog, preview, and export requests.
"""

from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

from app.domain.value_objects.report_types import ReportFormat, ReportType


class ReportCatalogResponse(BaseModel):
    """Catalog entry describing an available report type."""
    report_type: str
    title: str
    description: str
    supported_formats: list[str]
    filter_fields: list[str]


class ReportColumnSchema(BaseModel):
    """Definition of a table column for report preview."""
    key: str
    label: str
    align: str = "left"


class ReportPreviewResponse(BaseModel):
    """Sample slice of records and headers for front-end preview."""
    report_type: str
    title: str
    description: str
    generated_at: datetime
    columns: list[ReportColumnSchema]
    rows: list[dict[str, Any]]
    total_records: int


class ReportExportRequest(BaseModel):
    """Payload for generating and exporting an institutional report."""
    report_type: ReportType = Field(default=ReportType.INVENTORY, description="Tipo de reporte institucional")
    report_format: ReportFormat = Field(default=ReportFormat.EXCEL, description="Formato del archivo (EXCEL o PDF)")
    filters: dict[str, Any] = Field(default_factory=dict, description="Filtros específicos aplicables al reporte")
