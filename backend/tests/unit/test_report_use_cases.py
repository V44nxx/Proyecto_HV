"""
Unit tests for Report use cases:
- ListAvailableReportsUseCase
- GetReportPreviewUseCase
- GenerateReportUseCase
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
import uuid
import pytest

from app.application.use_cases.reports import (
    GenerateReportUseCase,
    GetReportPreviewUseCase,
    ListAvailableReportsUseCase,
)
from app.domain.value_objects.report_types import (
    ReportColumn,
    ReportDataset,
    ReportFormat,
    ReportType,
)


@pytest.fixture
def mock_report_dataset():
    now = datetime(2026, 9, 20, 10, 0, 0, tzinfo=timezone.utc)
    columns = [
        ReportColumn("number", "N°", width_excel=8, width_pdf_ratio=0.5, align="center"),
        ReportColumn("filename", "Nombre de Archivo", width_excel=25, width_pdf_ratio=2.0),
        ReportColumn("document_type", "Formato", width_excel=15, width_pdf_ratio=1.0, align="center"),
    ]
    rows = [
        {"number": 1, "filename": "cv_test.pdf", "document_type": "ATS"},
    ]
    return ReportDataset(
        report_type=ReportType.INVENTORY,
        title="Reporte de Inventario de Hojas de Vida",
        description="Listado de documentos cargados en la plataforma",
        generated_at=now,
        generated_by="user@test.com",
        applied_filters={},
        columns=columns,
        rows=rows,
        total_records=1,
    )


def test_list_available_reports_use_case():
    use_case = ListAvailableReportsUseCase()
    catalog = use_case.execute()

    assert len(catalog) == 6
    types = [item.report_type for item in catalog]
    assert ReportType.INVENTORY in types
    assert ReportType.PROFESSIONAL_CLASSIFICATION in types
    assert ReportType.ACADEMIC in types
    assert ReportType.EXPERIENCE in types
    assert ReportType.GEOGRAPHIC in types
    assert ReportType.CUSTOM_FILTERED in types

    for item in catalog:
        assert len(item.title) > 0
        assert len(item.description) > 0
        assert ReportFormat.EXCEL in item.supported_formats
        assert ReportFormat.PDF in item.supported_formats
        assert len(item.filter_fields) > 0


@pytest.mark.asyncio
async def test_get_report_preview_use_case(mock_report_dataset):
    mock_repo = AsyncMock()
    mock_repo.get_inventory_dataset.return_value = mock_report_dataset
    mock_repo.get_classification_dataset.return_value = mock_report_dataset
    mock_repo.get_academic_dataset.return_value = mock_report_dataset
    mock_repo.get_experience_dataset.return_value = mock_report_dataset
    mock_repo.get_geographic_dataset.return_value = mock_report_dataset
    mock_repo.get_custom_filtered_dataset.return_value = mock_report_dataset

    use_case = GetReportPreviewUseCase(mock_repo)

    # Test each report type preview
    for r_type in ReportType:
        res = await use_case.execute(
            report_type=r_type,
            filters={"test": 1},
            generated_by="user@test.com",
            preview_limit=15,
        )
        assert res == mock_report_dataset

    with pytest.raises(ValueError, match="Tipo de reporte no soportado"):
        await use_case.execute(
            report_type="NON_EXISTENT_TYPE",
            filters={},
            generated_by="user@test.com",
        )


@pytest.mark.asyncio
async def test_generate_report_use_case_excel(mock_report_dataset):
    mock_repo = AsyncMock()
    mock_repo.get_inventory_dataset.return_value = mock_report_dataset
    mock_repo.record_audit_log.return_value = MagicMock()

    mock_excel_gen = MagicMock()
    mock_excel_gen.generate.return_value = b"PK\x03\x04fake_excel_bytes"

    mock_pdf_gen = MagicMock()

    use_case = GenerateReportUseCase(
        report_repo=mock_repo,
        excel_gen=mock_excel_gen,
        pdf_gen=mock_pdf_gen,
    )

    user_id = uuid.uuid4()
    result = await use_case.execute(
        report_type=ReportType.INVENTORY,
        report_format=ReportFormat.EXCEL,
        filters={"status": "COMPLETED"},
        user_id=user_id,
        user_name="admin@test.com",
        ip_address="10.0.0.1",
        user_agent="PytestClient",
    )

    assert result.content == b"PK\x03\x04fake_excel_bytes"
    assert result.media_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert result.filename.endswith(".xlsx")
    assert result.total_records == 1

    # Verify audit log was recorded
    mock_repo.record_audit_log.assert_awaited_once()
    args, kwargs = mock_repo.record_audit_log.call_args
    assert kwargs["action"] == "EXPORT_REPORT"
    assert kwargs["user_id"] == user_id
    assert kwargs["ip_address"] == "10.0.0.1"
    assert kwargs["details"]["format"] == "EXCEL"


@pytest.mark.asyncio
async def test_generate_report_use_case_pdf(mock_report_dataset):
    mock_repo = AsyncMock()
    mock_repo.get_inventory_dataset.return_value = mock_report_dataset
    mock_repo.record_audit_log.return_value = MagicMock()

    mock_excel_gen = MagicMock()
    mock_pdf_gen = MagicMock()
    mock_pdf_gen.generate.return_value = b"%PDF-1.4 fake_pdf_bytes"

    use_case = GenerateReportUseCase(
        report_repo=mock_repo,
        excel_gen=mock_excel_gen,
        pdf_gen=mock_pdf_gen,
    )

    result = await use_case.execute(
        report_type=ReportType.INVENTORY,
        report_format=ReportFormat.PDF,
        filters={},
        user_id=None,
        user_name="anon",
    )

    assert result.content == b"%PDF-1.4 fake_pdf_bytes"
    assert result.media_type == "application/pdf"
    assert result.filename.endswith(".pdf")
    assert result.total_records == 1
    mock_pdf_gen.generate.assert_called_once_with(mock_report_dataset)
