"""
Documents API router.

Endpoints:
  POST   /api/v1/documents         - Upload PDF resume (documents:write)
  GET    /api/v1/documents         - List documents with pagination (documents:read)
  GET    /api/v1/documents/{id}     - Get document details and latest job (documents:read)
  GET    /api/v1/documents/{id}/file - Download or view original PDF (documents:read)
  DELETE /api/v1/documents/{id}     - Soft delete document (documents:delete)
  GET    /api/v1/documents/{id}/job  - Get processing job status (documents:read)
"""

import math
import uuid
from typing import Annotated

import structlog
from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)

from app.application.use_cases.documents.delete_document import DeleteDocumentUseCase
from app.application.use_cases.documents.download_document import DownloadDocumentUseCase
from app.application.use_cases.documents.exceptions import (
    DocumentNotFoundError,
    DuplicateDocumentError,
    FileTooLargeError,
    InvalidFileFormatError,
)
from app.application.use_cases.documents.get_document import GetDocumentUseCase
from app.application.use_cases.documents.list_documents import ListDocumentsUseCase
from app.application.use_cases.documents.upload_document import UploadDocumentUseCase
from app.presentation.dependencies.auth import (
    CurrentUser,
    require_permission,
)
from app.presentation.dependencies.document_dependencies import (
    DocumentRepo,
    Storage,
    UserRepo,
)
from app.presentation.schemas.document_schemas import (
    DocumentDetailResponse,
    DocumentListResponse,
    DocumentResponse,
    DocumentUploadResponse,
    ProcessingJobResponse,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/documents", tags=["Documentos"])


@router.post(
    "",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Subir hoja de vida en PDF",
    dependencies=[require_permission("documents", "write")],
)
async def upload_document(
    request: Request,
    current_user: CurrentUser,
    document_repo: DocumentRepo,
    user_repo: UserRepo,
    storage: Storage,
    file: UploadFile = File(..., description="Archivo PDF de la hoja de vida"),
) -> DocumentUploadResponse:
    """
    Sube un archivo PDF de hoja de vida, verifica su integridad, calcula su checksum SHA-256,
    detecta duplicados y crea el trabajo inicial de procesamiento asíncrono.
    """
    file_bytes = await file.read()
    filename = file.filename or "documento.pdf"
    content_type = file.content_type

    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    use_case = UploadDocumentUseCase(
        document_repo=document_repo,
        user_repo=user_repo,
        storage_provider=storage,
    )

    try:
        user_uuid = uuid.UUID(current_user.user_id)
        document, job = await use_case.execute(
            file_bytes=file_bytes,
            filename=filename,
            content_type=content_type,
            uploaded_by=user_uuid,
            ip_address=client_ip,
            user_agent=user_agent,
        )
    except InvalidFileFormatError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.message,
        ) from exc
    except FileTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=exc.message,
        ) from exc
    except DuplicateDocumentError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": exc.message,
                "existing_document_id": str(exc.existing_document_id),
                "existing_filename": exc.existing_filename,
            },
        ) from exc

    return DocumentUploadResponse(
        message="Documento subido exitosamente para procesamiento",
        document=DocumentResponse.model_validate(document),
        job=ProcessingJobResponse.model_validate(job),
    )


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="Listar documentos",
    dependencies=[require_permission("documents", "read")],
)
async def list_documents(
    document_repo: DocumentRepo,
    page: Annotated[int, Query(ge=1, description="Número de página")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Registros por página")] = 20,
    document_type: Annotated[str | None, Query(description="Filtrar por tipo (FORMATO_UNICO, ATS, UNKNOWN)")] = None,
    person_id: Annotated[uuid.UUID | None, Query(description="Filtrar por ID de persona")] = None,
) -> DocumentListResponse:
    """
    Lista los documentos subidos al sistema con paginación y filtros opcionales.
    """
    use_case = ListDocumentsUseCase(document_repo=document_repo)
    items, total = await use_case.execute(
        page=page,
        page_size=page_size,
        document_type=document_type,
        person_id=person_id,
    )

    total_pages = math.ceil(total / page_size) if total > 0 else 0

    return DocumentListResponse(
        items=[DocumentResponse.model_validate(d) for d in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/{document_id}",
    response_model=DocumentDetailResponse,
    summary="Detalle de un documento",
    dependencies=[require_permission("documents", "read")],
)
async def get_document(
    document_id: uuid.UUID,
    document_repo: DocumentRepo,
) -> DocumentDetailResponse:
    """
    Obtiene los metadatos de un documento y el estado de su último trabajo de procesamiento.
    """
    use_case = GetDocumentUseCase(document_repo=document_repo)
    try:
        doc, latest_job = await use_case.execute(document_id)
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.message,
        ) from exc

    return DocumentDetailResponse(
        document=DocumentResponse.model_validate(doc),
        latest_job=ProcessingJobResponse.model_validate(latest_job) if latest_job else None,
    )


@router.get(
    "/{document_id}/file",
    summary="Descargar o visualizar archivo PDF original",
    dependencies=[require_permission("documents", "read")],
)
async def download_document(
    document_id: uuid.UUID,
    request: Request,
    current_user: CurrentUser,
    document_repo: DocumentRepo,
    user_repo: UserRepo,
    storage: Storage,
) -> Response:
    """
    Descarga o sirve en línea el archivo PDF original de la hoja de vida almacenada.
    """
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    use_case = DownloadDocumentUseCase(
        document_repo=document_repo,
        user_repo=user_repo,
        storage_provider=storage,
    )

    try:
        user_uuid = uuid.UUID(current_user.user_id)
        file_bytes, filename, mime_type = await use_case.execute(
            document_id=document_id,
            requested_by=user_uuid,
            ip_address=client_ip,
            user_agent=user_agent,
        )
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.message,
        ) from exc

    # Sanitize header filename
    safe_filename = filename.replace('"', "").replace("\n", "").replace("\r", "")

    return Response(
        content=file_bytes,
        media_type=mime_type,
        headers={
            "Content-Disposition": f'inline; filename="{safe_filename}"',
            "Content-Length": str(len(file_bytes)),
        },
    )


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar documento (soft delete)",
    dependencies=[require_permission("documents", "delete")],
)
async def delete_document(
    document_id: uuid.UUID,
    request: Request,
    current_user: CurrentUser,
    document_repo: DocumentRepo,
    user_repo: UserRepo,
) -> None:
    """
    Realiza eliminación lógica (soft delete) del documento y registra auditoría.
    """
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    use_case = DeleteDocumentUseCase(
        document_repo=document_repo,
        user_repo=user_repo,
    )

    try:
        user_uuid = uuid.UUID(current_user.user_id)
        await use_case.execute(
            document_id=document_id,
            deleted_by=user_uuid,
            ip_address=client_ip,
            user_agent=user_agent,
        )
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.message,
        ) from exc


@router.get(
    "/{document_id}/job",
    response_model=ProcessingJobResponse,
    summary="Estado del trabajo de procesamiento",
    dependencies=[require_permission("documents", "read")],
)
async def get_document_job(
    document_id: uuid.UUID,
    document_repo: DocumentRepo,
) -> ProcessingJobResponse:
    """
    Consulta el estado actual del trabajo de procesamiento del documento para polling o tracking.
    """
    latest_job = await document_repo.get_latest_job_for_document(document_id)
    if not latest_job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró ningún trabajo de procesamiento para el documento {document_id}.",
        )

    return ProcessingJobResponse.model_validate(latest_job)
