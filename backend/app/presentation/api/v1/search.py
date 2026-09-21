"""
Search API router: candidate multi-criteria search, pagination, candidate dossier,
facets, filter options, and profession classification.
"""

from typing import Any
import uuid
import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.use_cases.search import (
    CandidateNotFoundError,
    ClassifyCandidateProfessionUseCase,
    GetCandidateDetailUseCase,
    GetFilterOptionsUseCase,
    GetSearchFacetsUseCase,
    SearchCandidatesUseCase,
)
from app.infrastructure.database.session import get_db_session
from app.presentation.dependencies.auth import require_permission
from app.presentation.dependencies.document_dependencies import SearchRepo
from app.presentation.schemas.search_schemas import (
    CandidateFullDetailResponse,
    CandidateSearchResponse,
    ClassifyProfessionResponse,
    FilterOptionsResponse,
    SearchFacetsResponse,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/search", tags=["Búsqueda Avanzada"])


@router.get(
    "/candidates",
    response_model=CandidateSearchResponse,
    summary="Búsqueda avanzada de candidatos con filtros multicriterio y paginación",
    dependencies=[require_permission("documents", "read")],
)
async def search_candidates_endpoint(
    search_repo: SearchRepo,
    q: str | None = Query(None, description="Búsqueda de texto libre sobre nombre, cédula, empresa, universidad o habilidades"),
    identification_number: str | None = Query(None, description="Número de documento de identidad"),
    name: str | None = Query(None, description="Nombre o apellidos del candidato"),
    category_id: uuid.UUID | None = Query(None, description="UUID de la categoría profesional"),
    profession_id: uuid.UUID | None = Query(None, description="UUID de la profesión canónica"),
    profession_name: str | None = Query(None, description="Nombre o alias de la profesión"),
    academic_level: str | None = Query(None, description="Nivel académico (UNDERGRADUATE, MASTER, etc.)"),
    institution: str | None = Query(None, description="Institución educativa o universidad"),
    company: str | None = Query(None, description="Empresa u organización en historial laboral"),
    position: str | None = Query(None, description="Cargo o puesto de trabajo"),
    department: str | None = Query(None, description="Departamento de residencia"),
    municipality: str | None = Query(None, description="Municipio de residencia"),
    min_years_experience: int | None = Query(None, ge=0, description="Mínimo de años de experiencia"),
    max_years_experience: int | None = Query(None, ge=0, description="Máximo de años de experiencia"),
    language: str | None = Query(None, description="Idioma conocido"),
    skills: str | None = Query(None, description="Habilidad técnica o competencia"),
    certification: str | None = Query(None, description="Nombre de certificación"),
    document_type: str | None = Query(None, description="Tipo de documento fuente (FORMATO_UNICO o ATS)"),
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(20, ge=1, le=100, description="Cantidad de registros por página"),
    sort_by: str = Query("created_at", pattern="^(created_at|name|experience)$", description="Campo de ordenación"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Dirección del orden (asc o desc)"),
) -> CandidateSearchResponse:
    """
    Ejecuta una búsqueda avanzada de candidatos combinando texto libre y filtros estructurados
    con paginación y ordenamiento en el servidor.
    """
    filters = {
        "q": q,
        "identification_number": identification_number,
        "name": name,
        "category_id": category_id,
        "profession_id": profession_id,
        "profession_name": profession_name,
        "academic_level": academic_level,
        "institution": institution,
        "company": company,
        "position": position,
        "department": department,
        "municipality": municipality,
        "min_years_experience": min_years_experience,
        "max_years_experience": max_years_experience,
        "language": language,
        "skills": skills,
        "certification": certification,
        "document_type": document_type,
    }

    use_case = SearchCandidatesUseCase(search_repo=search_repo)
    return await use_case.execute(
        filters=filters,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.get(
    "/candidates/{person_id}",
    response_model=CandidateFullDetailResponse,
    summary="Consultar dossier integral del candidato",
    dependencies=[require_permission("documents", "read")],
)
async def get_candidate_detail_endpoint(
    person_id: uuid.UUID,
    search_repo: SearchRepo,
) -> CandidateFullDetailResponse:
    """
    Retorna la ficha y dossier consolidado del candidato con todos sus datos personales,
    contacto, formación académica, experiencia laboral, resumen, habilidades y documentos.
    """
    use_case = GetCandidateDetailUseCase(search_repo=search_repo)
    try:
        return await use_case.execute(person_id=person_id)
    except CandidateNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.message,
        ) from exc


@router.get(
    "/facets",
    response_model=SearchFacetsResponse,
    summary="Métricas y conteos agregados para facetas de búsqueda",
    dependencies=[require_permission("documents", "read")],
)
async def get_search_facets_endpoint(
    search_repo: SearchRepo,
) -> SearchFacetsResponse:
    """
    Retorna estadísticas agregadas por categorías profesionales, profesiones más comunes,
    niveles educativos y departamentos geográficos.
    """
    use_case = GetSearchFacetsUseCase(search_repo=search_repo)
    return await use_case.execute()


@router.get(
    "/filter-options",
    response_model=FilterOptionsResponse,
    summary="Opciones de filtros para selectores de la interfaz",
    dependencies=[require_permission("documents", "read")],
)
async def get_filter_options_endpoint(
    search_repo: SearchRepo,
) -> FilterOptionsResponse:
    """
    Retorna el catálogo taxonómico de categorías, profesiones, niveles académicos
    y departamentos colombianos para poblar los controles de filtro en la interfaz de usuario.
    """
    use_case = GetFilterOptionsUseCase(search_repo=search_repo)
    return await use_case.execute()


@router.post(
    "/candidates/{person_id}/classify-profession",
    response_model=ClassifyProfessionResponse,
    summary="Clasificar automáticamente profesión y categoría canónica del candidato",
    dependencies=[require_permission("documents", "write")],
)
async def classify_candidate_profession_endpoint(
    person_id: uuid.UUID,
    search_repo: SearchRepo,
    db: AsyncSession = Depends(get_db_session),
) -> ClassifyProfessionResponse:
    """
    Evalúa la trayectoria académica y profesional de una persona para clasificarla y asignarla
    a su categoría y profesión canónica correspondiente.
    """
    use_case = ClassifyCandidateProfessionUseCase(db=db, search_repo=search_repo)
    try:
        return await use_case.execute(person_id=person_id)
    except CandidateNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.message,
        ) from exc
