"""
Domain value objects for reporting and document export.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class ReportType(StrEnum):
    """Supported institutional report categories."""
    INVENTORY = "INVENTORY"
    PROFESSIONAL_CLASSIFICATION = "PROFESSIONAL_CLASSIFICATION"
    ACADEMIC = "ACADEMIC"
    EXPERIENCE = "EXPERIENCE"
    GEOGRAPHIC = "GEOGRAPHIC"
    CUSTOM_FILTERED = "CUSTOM_FILTERED"


class ReportFormat(StrEnum):
    """Supported binary export document formats."""
    EXCEL = "EXCEL"
    PDF = "PDF"


@dataclass(frozen=True)
class ReportColumn:
    """Column definition for tabular report presentation."""
    key: str
    label: str
    width_excel: int = 20
    width_pdf_ratio: float = 1.0
    align: str = "left"  # "left", "center", "right"


@dataclass
class ReportDataset:
    """Consolidated dataset ready for PDF or Excel rendering."""
    report_type: ReportType
    title: str
    description: str
    generated_at: datetime
    generated_by: str
    applied_filters: dict[str, Any]
    columns: list[ReportColumn]
    rows: list[dict[str, Any]]
    total_records: int = 0

    def __post_init__(self) -> None:
        if not self.total_records:
            self.total_records = len(self.rows)
