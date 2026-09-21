"""
API routes for Human-in-the-Loop review of extracted document fields.
"""

from typing import Any
import uuid
import structlog
from fastapi import APIRouter, HTTPException, Query, status

from app.application.use_cases.documents.exceptions import DocumentNotFoundError
from app.application.use_cases.reviews import (
    BatchReviewFieldsUseCase,
    FinalizeDocumentReviewUseCase,
    GetReviewSummaryUseCase,
    ListReviewFieldsUseCase,
    ReviewFieldUseCase,
)
from app.presentation.dependencies.auth import CurrentUser, require_permission
from app.presentation.dependencies.document_dependencies import (
    DocumentRepo,
    PersonRepo,
    ReviewRepo,
)
from app.presentation.schemas.review_schemas import (
    BatchReviewRequest,
    CorrectFieldRequest,
    FinalizeReviewResponse,
    RejectFieldRequest,
    ReviewFieldResponse,
    ReviewSummaryResponse,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/documents", tags=["Revisión Humana"])


@router.get(
    "/{document_id}/review-fields",
    response_model=list[ReviewFieldResponse],
    summary="Listar campos extraídos para revisión humana",
    dependencies=[require_permission("documents", "read")],
)
async def list_review_fields_endpoint(
    document_id: uuid.UUID,
    document_repo: DocumentRepo,
    review_repo: ReviewRepo,
    status_filter: str | None = Query(None, alias="status", description="Filtrar por estado (PENDING, ACCEPTED, CORRECTED, REJECTED)"),
    page_number: int | None = Query(None, description="Filtrar por número de página"),
) -> list[ReviewFieldResponse]:
    """
    Retorna los campos extraídos del documento para auditoría humana y corrección.
    """
    use_case = ListReviewFieldsUseCase(
        document_repo=document_repo,
        review_repo=review_repo,
    )
    try:
        fields = await use_case.execute(
            document_id=document_id,
            status_filter=status_filter,
            page_number=page_number,
        )
        return [ReviewFieldResponse.model_validate(f) for f in fields]
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.message,
        ) from exc


@router.get(
    "/{document_id}/review-summary",
    response_model=ReviewSummaryResponse,
    summary="Consultar resumen y progreso de revisión humana",
    dependencies=[require_permission("documents", "read")],
)
async def get_review_summary_endpoint(
    document_id: uuid.UUID,
    document_repo: DocumentRepo,
    review_repo: ReviewRepo,
) -> ReviewSummaryResponse:
    """
    Retorna métricas de campos revisados, pendientes y porcentaje de avance.
    """
    use_case = GetReviewSummaryUseCase(
        document_repo=document_repo,
        review_repo=review_repo,
    )
    try:
        summary = await use_case.execute(document_id)
        return ReviewSummaryResponse(**summary)
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.message,
        ) from exc


@router.post(
    "/{document_id}/review-fields/{field_id}/accept",
    response_model=ReviewFieldResponse,
    summary="Aceptar campo extraído como verificado",
    dependencies=[require_permission("documents", "write")],
)
async def accept_field_endpoint(
    document_id: uuid.UUID,
    field_id: uuid.UUID,
    document_repo: DocumentRepo,
    person_repo: PersonRepo,
    review_repo: ReviewRepo,
    current_user: CurrentUser,
) -> ReviewFieldResponse:
    """
    Marca un campo extraído como válido y aprobado por un revisor humano.
    """
    use_case = ReviewFieldUseCase(
        document_repo=document_repo,
        person_repo=person_repo,
        review_repo=review_repo,
    )
    reviewer_id = uuid.UUID(current_user.user_id) if current_user.user_id else None
    try:
        field = await use_case.accept_field(
            document_id=document_id,
            field_id=field_id,
            reviewer_id=reviewer_id,
        )
        return ReviewFieldResponse.model_validate(field)
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.message,
        ) from exc


@router.post(
    "/{document_id}/review-fields/{field_id}/correct",
    response_model=ReviewFieldResponse,
    summary="Corregir valor de campo extraído con propagación",
    dependencies=[require_permission("documents", "write")],
)
async def correct_field_endpoint(
    document_id: uuid.UUID,
    field_id: uuid.UUID,
    payload: CorrectFieldRequest,
    document_repo: DocumentRepo,
    person_repo: PersonRepo,
    review_repo: ReviewRepo,
    current_user: CurrentUser,
) -> ReviewFieldResponse:
    """
    Modifica el valor de un campo, propaga la corrección a la Persona/Contacto y audita.
    """
    use_case = ReviewFieldUseCase(
        document_repo=document_repo,
        person_repo=person_repo,
        review_repo=review_repo,
    )
    reviewer_id = uuid.UUID(current_user.user_id) if current_user.user_id else None
    try:
        field = await use_case.correct_field(
            document_id=document_id,
            field_id=field_id,
            corrected_value=payload.corrected_value,
            note=payload.note,
            reviewer_id=reviewer_id,
        )
        return ReviewFieldResponse.model_validate(field)
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.message,
        ) from exc


@router.post(
    "/{document_id}/review-fields/{field_id}/reject",
    response_model=ReviewFieldResponse,
    summary="Rechazar campo extraído inválido",
    dependencies=[require_permission("documents", "write")],
)
async def reject_field_endpoint(
    document_id: uuid.UUID,
    field_id: uuid.UUID,
    payload: RejectFieldRequest,
    document_repo: DocumentRepo,
    person_repo: PersonRepo,
    review_repo: ReviewRepo,
    current_user: CurrentUser,
) -> ReviewFieldResponse:
    """
    Rechaza un campo extraído erróneo registrando el motivo.
    """
    use_case = ReviewFieldUseCase(
        document_repo=document_repo,
        person_repo=person_repo,
        review_repo=review_repo,
    )
    reviewer_id = uuid.UUID(current_user.user_id) if current_user.user_id else None
    try:
        field = await use_case.reject_field(
            document_id=document_id,
            field_id=field_id,
            reason=payload.reason,
            reviewer_id=reviewer_id,
        )
        return ReviewFieldResponse.model_validate(field)
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.message,
        ) from exc


@router.post(
    "/{document_id}/review-fields/batch",
    summary="Aprobación o rechazo masivo de campos por lotes",
    dependencies=[require_permission("documents", "write")],
)
async def batch_review_endpoint(
    document_id: uuid.UUID,
    payload: BatchReviewRequest,
    document_repo: DocumentRepo,
    review_repo: ReviewRepo,
    current_user: CurrentUser,
) -> dict[str, Any]:
    """
    Aplica una acción en lote (ACCEPT o REJECT) sobre una lista de IDs de campos.
    """
    use_case = BatchReviewFieldsUseCase(
        document_repo=document_repo,
        review_repo=review_repo,
    )
    reviewer_id = uuid.UUID(current_user.user_id) if current_user.user_id else None
    try:
        updated_count = await use_case.execute(
            document_id=document_id,
            field_ids=payload.field_ids,
            action=payload.action,
            reviewer_id=reviewer_id,
        )
        return {
            "message": f"{updated_count} campos actualizados exitosamente a {payload.action.upper()}",
            "updated_count": updated_count,
        }
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.message,
        ) from exc


@router.post(
    "/{document_id}/finalize-review",
    response_model=FinalizeReviewResponse,
    summary="Finalizar revisión humana y aprobar documento",
    dependencies=[require_permission("documents", "write")],
)
async def finalize_review_endpoint(
    document_id: uuid.UUID,
    document_repo: DocumentRepo,
    review_repo: ReviewRepo,
    current_user: CurrentUser,
) -> FinalizeReviewResponse:
    """
    Cierra formalmente el ciclo de revisión humana y avanza el trabajo a COMPLETED al 100%.
    """
    use_case = FinalizeDocumentReviewUseCase(
        document_repo=document_repo,
        review_repo=review_repo,
    )
    reviewer_id = uuid.UUID(current_user.user_id) if current_user.user_id else None
    try:
        result = await use_case.execute(
            document_id=document_id,
            reviewer_id=reviewer_id,
        )
        return FinalizeReviewResponse(**result)
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.message,
        ) from exc
