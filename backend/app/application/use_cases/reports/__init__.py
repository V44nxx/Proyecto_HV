"""
Reports use cases package.
"""

from app.application.use_cases.reports.generate_report import (
    GeneratedReportResult,
    GenerateReportUseCase,
)
from app.application.use_cases.reports.get_report_preview import (
    GetReportPreviewUseCase,
)
from app.application.use_cases.reports.list_available_reports import (
    AvailableReportInfo,
    ListAvailableReportsUseCase,
)

__all__ = [
    "AvailableReportInfo",
    "ListAvailableReportsUseCase",
    "GetReportPreviewUseCase",
    "GeneratedReportResult",
    "GenerateReportUseCase",
]
