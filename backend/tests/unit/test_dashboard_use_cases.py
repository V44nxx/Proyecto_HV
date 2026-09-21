"""
Unit tests for Dashboard use cases:
- GetDashboardKpisUseCase
- GetDashboardDistributionsUseCase
- GetDashboardOverviewUseCase
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock
import uuid
import pytest

from app.application.use_cases.dashboard import (
    GetDashboardDistributionsUseCase,
    GetDashboardKpisUseCase,
    GetDashboardOverviewUseCase,
)
from app.presentation.schemas.dashboard_schemas import (
    DashboardDistributionsResponse,
    DashboardKpiResponse,
    DashboardOverviewResponse,
)


@pytest.fixture
def mock_dashboard_repo():
    repo = AsyncMock()
    repo.get_kpis.return_value = {
        "total_documents": 20,
        "total_persons": 18,
        "total_professionals": 15,
        "processed_documents": 16,
        "documents_requiring_review": 3,
        "extraction_success_rate": 80.0,
    }
    repo.get_format_distribution.return_value = [
        {"label": "FORMATO_UNICO", "count": 12, "percentage": 60.0},
        {"label": "ATS_RESUME", "count": 8, "percentage": 40.0},
    ]
    repo.get_category_distribution.return_value = [
        {"label": "Ingeniería y Tecnología", "count": 10, "percentage": 66.7},
        {"label": "Administración", "count": 5, "percentage": 33.3},
    ]
    repo.get_top_professions.return_value = [
        {"label": "Ingeniero de Software", "count": 6, "percentage": 60.0},
        {"label": "Contador Público", "count": 4, "percentage": 40.0},
    ]
    repo.get_academic_level_distribution.return_value = [
        {"label": "UNDERGRADUATE", "count": 14, "percentage": 70.0},
        {"label": "POSTGRADUATE", "count": 6, "percentage": 30.0},
    ]
    repo.get_experience_distribution.return_value = {
        "0_to_2_years": 4,
        "3_to_5_years": 8,
        "6_to_10_years": 5,
        "more_than_10_years": 3,
    }
    repo.get_geographic_distribution.return_value = [
        {"label": "Bogotá D.C.", "count": 12, "percentage": 60.0},
        {"label": "Antioquia", "count": 8, "percentage": 40.0},
    ]
    now = datetime.now(timezone.utc)
    repo.get_documents_requiring_review.return_value = [
        {
            "document_id": uuid.uuid4(),
            "filename": "cv_candidate.pdf",
            "document_type": "ATS_RESUME",
            "job_id": uuid.uuid4(),
            "current_step": "review_required",
            "error_message": "Low confidence",
            "created_at": now,
        }
    ]
    repo.get_recent_activity.return_value = [
        {
            "document_id": uuid.uuid4(),
            "filename": "cv_candidate.pdf",
            "document_type": "ATS_RESUME",
            "candidate_name": "Carlos Gomez",
            "person_id": uuid.uuid4(),
            "status": "COMPLETED",
            "file_size_bytes": 204800,
            "created_at": now,
        }
    ]
    return repo


@pytest.mark.asyncio
async def test_get_dashboard_kpis_use_case(mock_dashboard_repo):
    use_case = GetDashboardKpisUseCase(mock_dashboard_repo)
    result = await use_case.execute()

    assert isinstance(result, DashboardKpiResponse)
    assert result.total_documents == 20
    assert result.total_persons == 18
    assert result.total_professionals == 15
    assert result.processed_documents == 16
    assert result.documents_requiring_review == 3
    assert result.extraction_success_rate == 80.0
    mock_dashboard_repo.get_kpis.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_dashboard_distributions_use_case(mock_dashboard_repo):
    use_case = GetDashboardDistributionsUseCase(mock_dashboard_repo)
    result = await use_case.execute()

    assert isinstance(result, DashboardDistributionsResponse)
    assert len(result.by_format) == 2
    assert result.by_format[0].label == "FORMATO_UNICO"
    assert len(result.by_category) == 2
    assert len(result.top_professions) == 2
    assert len(result.by_academic_level) == 2
    assert result.by_experience["3_to_5_years"] == 8
    assert len(result.by_geography) == 2


@pytest.mark.asyncio
async def test_get_dashboard_overview_use_case(mock_dashboard_repo):
    use_case = GetDashboardOverviewUseCase(mock_dashboard_repo)
    result = await use_case.execute()

    assert isinstance(result, DashboardOverviewResponse)
    assert result.kpis.total_documents == 20
    assert len(result.distributions.by_format) == 2
    assert len(result.pending_reviews) == 1
    assert result.pending_reviews[0].filename == "cv_candidate.pdf"
    assert len(result.recent_activity) == 1
    assert result.recent_activity[0].candidate_name == "Carlos Gomez"
