"""
Reports API router: catalog, preview, and streaming export in Excel (.xlsx) and PDF (.pdf).
"""

from typing import Any
import uuid
import structlog
from fastapi import APIRouter, Depends, Query, Request, Response, status

from app.application.use_cases.reports import (
    GenerateReportUseCase,
    GetReportPreviewUseCase,
    ListAvailableReportsUseCase,
)
from app.domain.value_objects.report_types import ReportFormat, ReportType
from app.presentation.dependencies.auth import (
    AuthenticatedUser,
    get_current_user,
    require_permission,
)
from app.presentation.dependencies.document_dependencies import ReportRepo
from app.presentation.schemas.report_schemas import (
    ReportCatalogResponse,
    ReportColumnSchema,
    ReportExportRequest,
    ReportPreviewResponse,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/reports", tags=["Módulo de Reportes"])


@router.get(
    "",
    response_model=list[ReportCatalogResponse],
    summary="Obtener catálogo de reportes institucionales disponibles",
    dependencies=[require_permission("documents", "read")],
)
async def list_reports_catalog() -> list[ReportCatalogResponse]:
    """
    Retorna la lista de reportes disponibles en el sistema con sus descripciones,
    formatos soportados (Excel / PDF) y campos de filtrado aceptados.
    """
    use_case = ListAvailableReportsUseCase()
    catalog = use_case.execute()
    return [
        ReportCatalogResponse(
            report_type=item.report_type.value,
            title=item.title,
            description=item.description,
            supported_formats=[fmt.value for fmt in item.supported_formats],
            filter_fields=item.filter_fields,
        )
        for item in catalog
    ]


@router.post(
    "/preview",
    response_model=ReportPreviewResponse,
    summary="Previsualizar muestra de datos antes de exportar",
    dependencies=[require_permission("documents", "read")],
)
async def preview_report(
    req: ReportExportRequest,
    report_repo: ReportRepo,
    current_user: AuthenticatedUser = Depends(get_current_user),
    limit: int = Query(20, ge=1, le=100, description="Cantidad de registros de muestra"),
) -> ReportPreviewResponse:
    """
    Permite a la interfaz web previsualizar las columnas y las primeras filas
    coincidentes con los filtros seleccionados antes de realizar la descarga completa.
    """
    use_case = GetReportPreviewUseCase(report_repo)
    user_name = current_user.user_id
    dataset = await use_case.execute(
        report_type=req.report_type,
        filters=req.filters,
        generated_by=user_name,
        preview_limit=limit,
    )

    columns = [
        ReportColumnSchema(key=col.key, label=col.label, align=col.align)
        for col in dataset.columns
    ]

    return ReportPreviewResponse(
        report_type=dataset.report_type.value,
        title=dataset.title,
        description=dataset.description,
        generated_at=dataset.generated_at,
        columns=columns,
        rows=dataset.rows,
        total_records=dataset.total_records,
    )


@router.post(
    "/export",
    summary="Generar y descargar reporte institucional en Excel (.xlsx) o PDF (.pdf)",
    dependencies=[require_permission("documents", "read")],
)
async def export_report_post(
    req: ReportExportRequest,
    report_repo: ReportRepo,
    request: Request,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> Response:
    """
    Genera el archivo en formato Excel o PDF con los filtros solicitados,
    registra el evento en la auditoría inmutable del sistema y retorna el binario para descarga.
    """
    use_case = GenerateReportUseCase(report_repo)

    user_uuid = None
    try:
        user_uuid = uuid.UUID(current_user.user_id)
    except (ValueError, TypeError):
        pass

    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    result = await use_case.execute(
        report_type=req.report_type,
        report_format=req.report_format,
        filters=req.filters,
        user_id=user_uuid,
        user_name=current_user.user_id,
        ip_address=client_ip,
        user_agent=user_agent,
    )

    return Response(
        content=result.content,
        media_type=result.media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{result.filename}"',
            "X-Total-Records": str(result.total_records),
        },
    )


@router.get(
    "/export",
    summary="Descargar reporte institucional directamente mediante parámetros de consulta",
    dependencies=[require_permission("documents", "read")],
)
async def export_report_get(
    report_repo: ReportRepo,
    request: Request,
    current_user: AuthenticatedUser = Depends(get_current_user),
    report_type: ReportType = Query(ReportType.INVENTORY, description="Tipo de reporte"),
    report_format: ReportFormat = Query(ReportFormat.EXCEL, description="Formato (EXCEL o PDF)"),
    document_type: str | None = Query(None, description="Filtro de formato de hoja de vida"),
    status: str | None = Query(None, description="Filtro de estado de procesamiento"),
    category_id: uuid.UUID | None = Query(None, description="UUID de categoría profesional"),
    profession_name: str | None = Query(None, description="Nombre o alias de profesión"),
    department: str | None = Query(None, description="Departamento de residencia"),
    municipality: str | None = Query(None, description="Municipio de residencia"),
    academic_level: str | None = Query(None, description="Nivel académico"),
    min_years_experience: int | None = Query(None, ge=0, description="Mínimo de años de experiencia"),
    max_years_experience: int | None = Query(None, ge=0, description="Máximo de años de experiencia"),
) -> Response:
    """
    Permite invocar la descarga directa desde hipervínculos del navegador o botones directos.
    """
    filters = {}
    if document_type:
        filters["document_type"] = document_type
    if status:
        filters["status"] = status
    if category_id:
        filters["category_id"] = category_id
    if profession_name:
        filters["profession_name"] = profession_name
    if department:
        filters["department"] = department
    if municipality:
        filters["municipality"] = municipality
    if academic_level:
        filters["academic_level"] = academic_level
    if min_years_experience is not None:
        filters["min_years_experience"] = min_years_experience
    if max_years_experience is not None:
        filters["max_years_experience"] = max_years_experience

    use_case = GenerateReportUseCase(report_repo)

    user_uuid = None
    try:
        user_uuid = uuid.UUID(current_user.user_id)
    except (ValueError, TypeError):
        pass

    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    result = await use_case.execute(
        report_type=report_type,
        report_format=report_format,
        filters=filters,
        user_id=user_uuid,
        user_name=current_user.user_id,
        ip_address=client_ip,
        user_agent=user_agent,
    )

    return Response(
        content=result.content,
        media_type=result.media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{result.filename}"',
            "X-Total-Records": str(result.total_records),
        },
    )
