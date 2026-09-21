"""
Dashboard API router: executive KPIs, format & demographic distributions,
pending human review queue, and real-time processing activity feeds.
"""

from typing import Any
import structlog
from fastapi import APIRouter, Query, status

from app.application.use_cases.dashboard import (
    GetDashboardDistributionsUseCase,
    GetDashboardKpisUseCase,
    GetDashboardOverviewUseCase,
)
from app.presentation.dependencies.auth import require_permission
from app.presentation.dependencies.document_dependencies import DashboardRepo
from app.presentation.schemas.dashboard_schemas import (
    DashboardDistributionsResponse,
    DashboardKpiResponse,
    DashboardOverviewResponse,
    PendingReviewItem,
    RecentActivityItem,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/dashboard", tags=["Panel de Control y Analítica"])


@router.get(
    "/overview",
    response_model=DashboardOverviewResponse,
    summary="Obtener vista consolidada del panel de control (KPIs, distribuciones, pendientes y actividad)",
    dependencies=[require_permission("documents", "read")],
)
async def get_dashboard_overview_endpoint(
    dashboard_repo: DashboardRepo,
) -> DashboardOverviewResponse:
    """
    Retorna métricas ejecutivas consolidadas en una sola petición:
    - Indicadores clave de rendimiento (KPIs)
    - Distribuciones por formato, categoría, profesión, nivel académico, experiencia y geografía
    - Cola de documentos que requieren revisión humana
    - Feed de actividad y procesamiento reciente
    """
    use_case = GetDashboardOverviewUseCase(dashboard_repo)
    return await use_case.execute()


@router.get(
    "/kpis",
    response_model=DashboardKpiResponse,
    summary="Obtener indicadores clave de rendimiento (KPIs) operativos y ejecutivos",
    dependencies=[require_permission("documents", "read")],
)
async def get_dashboard_kpis_endpoint(
    dashboard_repo: DashboardRepo,
) -> DashboardKpiResponse:
    """
    Retorna los KPIs principales del sistema:
    - Total de documentos registrados
    - Total de personas registradas
    - Total de profesionales clasificados
    - Documentos procesados exitosamente
    - Documentos que requieren revisión humana
    - Tasa porcentual de éxito de extracción
    """
    use_case = GetDashboardKpisUseCase(dashboard_repo)
    return await use_case.execute()


@router.get(
    "/distributions",
    response_model=DashboardDistributionsResponse,
    summary="Obtener distribuciones analíticas multicriterio del repositorio",
    dependencies=[require_permission("documents", "read")],
)
async def get_dashboard_distributions_endpoint(
    dashboard_repo: DashboardRepo,
) -> DashboardDistributionsResponse:
    """
    Retorna distribuciones estadísticas para visualización gráfica:
    - Por formato (Formato Único DAFP vs ATS Libre)
    - Por categoría profesional
    - Top profesiones normalizadas
    - Por nivel de educación alcanzado
    - Por rangos de años de experiencia
    - Por departamento geográfico
    """
    use_case = GetDashboardDistributionsUseCase(dashboard_repo)
    return await use_case.execute()


@router.get(
    "/pending-reviews",
    response_model=list[PendingReviewItem],
    summary="Obtener cola de documentos pendientes de revisión humana",
    dependencies=[require_permission("documents", "read")],
)
async def get_pending_reviews_endpoint(
    dashboard_repo: DashboardRepo,
    limit: int = Query(10, ge=1, le=100, description="Cantidad máxima de documentos a listar"),
) -> list[PendingReviewItem]:
    """
    Retorna los documentos con trabajos de procesamiento en estado REVIEW_REQUIRED
    o paso actual de revisión requerida, ordenados por fecha de creación descendente.
    """
    items = await dashboard_repo.get_documents_requiring_review(limit=limit)
    return [PendingReviewItem(**i) for i in items]


@router.get(
    "/recent-activity",
    response_model=list[RecentActivityItem],
    summary="Obtener feed cronológico de documentos y procesamientos recientes",
    dependencies=[require_permission("documents", "read")],
)
async def get_recent_activity_endpoint(
    dashboard_repo: DashboardRepo,
    limit: int = Query(10, ge=1, le=100, description="Cantidad máxima de eventos a listar"),
) -> list[RecentActivityItem]:
    """
    Retorna los últimos documentos cargados al repositorio con el nombre del candidato
    asociado (si ya fue identificado) y el estado más reciente de procesamiento.
    """
    items = await dashboard_repo.get_recent_activity(limit=limit)
    return [RecentActivityItem(**i) for i in items]
