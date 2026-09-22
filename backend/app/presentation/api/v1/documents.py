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
from datetime import date
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

from app.application.use_cases.documents.classify_document import ClassifyDocumentUseCase
from app.application.use_cases.documents.delete_document import DeleteDocumentUseCase
from app.application.use_cases.documents.download_document import DownloadDocumentUseCase
from app.application.use_cases.documents.exceptions import (
    DocumentNotFoundError,
    DuplicateDocumentError,
    FileTooLargeError,
    InvalidFileFormatError,
)
from app.application.use_cases.documents.extract_ats_resume import ExtractAtsResumeUseCase
from app.application.use_cases.documents.extract_formato_unico import ExtractFormatoUnicoUseCase
from app.application.use_cases.documents.get_canonical_resume import GetCanonicalResumeUseCase
from app.application.use_cases.documents.get_document import GetDocumentUseCase
from app.application.use_cases.documents.list_documents import ListDocumentsUseCase
from app.application.use_cases.documents.process_document_text import ProcessDocumentTextUseCase
from app.application.use_cases.documents.upload_document import UploadDocumentUseCase
from app.config.constants import DocumentType
from app.presentation.dependencies.auth import (
    CurrentUser,
    require_permission,
)
from app.presentation.dependencies.document_dependencies import (
    DocumentRepo,
    OCR,
    PersonRepo,
    Storage,
    UserRepo,
)
from app.presentation.schemas.document_schemas import (
    CanonicalContactResponse,
    CanonicalEducationResponse,
    CanonicalExperienceSummaryResponse,
    CanonicalLanguageResponse,
    CanonicalPersonResponse,
    CanonicalResumeResponse,
    CanonicalWorkExperienceResponse,
    ClassificationResponse,
    DocumentDetailResponse,
    DocumentExtractionResponse,
    DocumentListResponse,
    DocumentResponse,
    DocumentUploadResponse,
    ProcessingJobResponse,
    ProcessTextResponse,
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
    person_repo: PersonRepo,
    user_repo: UserRepo,
    storage: Storage,
    file: UploadFile = File(..., description="Archivo PDF de la hoja de vida"),
) -> DocumentUploadResponse:
    """
    Sube un archivo PDF de hoja de vida, verifica su integridad, calcula su checksum SHA-256,
    detecta duplicados y crea el trabajo inicial de procesamiento asíncrono.
    Ejecuta la clasificación y extracción automática inicial de datos.
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

    # Auto-clasificación y auto-extracción inmediata
    try:
        classify_use_case = ClassifyDocumentUseCase(
            document_repo=document_repo,
            storage_provider=storage,
        )
        cls_res = await classify_use_case.execute(document.id)
        doc_type = cls_res.document_type.value if hasattr(cls_res.document_type, "value") else str(cls_res.document_type)

        if doc_type == DocumentType.ATS.value:
            ats_use = ExtractAtsResumeUseCase(
                document_repo=document_repo,
                person_repo=person_repo,
                storage_provider=storage,
            )
            await ats_use.execute(document.id)
        else:
            fu_use = ExtractFormatoUnicoUseCase(
                document_repo=document_repo,
                person_repo=person_repo,
                storage_provider=storage,
            )
            await fu_use.execute(document.id)

        document = await document_repo.get_by_id(document.id) or document
        latest_job = await document_repo.get_latest_job_for_document(document.id)
        if latest_job:
            job = latest_job
    except Exception as exc:
        logger.warning("auto_extraction_on_upload_deferred", error=str(exc))

    return DocumentUploadResponse(
        message="Documento subido y procesado exitosamente",
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
@router.get(
    "/{document_id}/download",
    summary="Descargar o visualizar archivo PDF original (alias)",
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


@router.post(
    "/{document_id}/process-text",
    response_model=ProcessTextResponse,
    summary="Ejecutar extracción de texto y OCR",
    dependencies=[require_permission("documents", "write")],
)
async def process_document_text(
    document_id: uuid.UUID,
    document_repo: DocumentRepo,
    storage: Storage,
    ocr: OCR,
) -> ProcessTextResponse:
    """
    Inicia la extracción de texto nativo con PyMuPDF y ejecuta OCR en páginas escaneadas.
    Persiste los registros de extracción y actualiza el estado del trabajo.
    """
    use_case = ProcessDocumentTextUseCase(
        document_repo=document_repo,
        storage_provider=storage,
        ocr_provider=ocr,
    )

    try:
        ocr_result = await use_case.execute(document_id)
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.message,
        ) from exc
    except Exception as exc:
        logger.error("text_processing_failed", document_id=str(document_id), error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error durante el procesamiento de texto: {exc}",
        ) from exc

    preview = ocr_result.full_text[:300] + "..." if len(ocr_result.full_text) > 300 else ocr_result.full_text

    return ProcessTextResponse(
        message="Extracción de texto completada exitosamente",
        document_id=document_id,
        provider=ocr_result.provider,
        pages_count=ocr_result.page_count,
        overall_confidence=ocr_result.overall_confidence,
        processing_ms=ocr_result.processing_ms,
        full_text_preview=preview,
    )


@router.get(
    "/{document_id}/extractions",
    response_model=list[DocumentExtractionResponse],
    summary="Obtener extracciones de texto de un documento",
    dependencies=[require_permission("documents", "read")],
)
async def get_document_extractions(
    document_id: uuid.UUID,
    document_repo: DocumentRepo,
) -> list[DocumentExtractionResponse]:
    """
    Retorna la lista de extracciones por página registradas para el documento.
    """
    doc = await document_repo.get_by_id(document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Documento con ID {document_id} no encontrado.",
        )

    extractions = await document_repo.get_extractions_for_document(document_id)
    return [DocumentExtractionResponse.model_validate(e) for e in extractions]


@router.post(
    "/{document_id}/classify",
    response_model=ClassificationResponse,
    summary="Clasificar formato de hoja de vida (Formato Único DAFP vs ATS)",
    dependencies=[require_permission("documents", "write")],
)
async def classify_document_endpoint(
    document_id: uuid.UUID,
    document_repo: DocumentRepo,
    storage: Storage,
) -> ClassificationResponse:
    """
    Ejecuta el servicio de clasificación sobre el documento para determinar si es
    Formato Único de la Función Pública, ATS o Desconocido.
    """
    use_case = ClassifyDocumentUseCase(
        document_repo=document_repo,
        storage_provider=storage,
    )
    try:
        result = await use_case.execute(document_id)
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.message,
        ) from exc
    except Exception as exc:
        logger.error("classification_failed", document_id=str(document_id), error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error durante la clasificación del documento: {exc}",
        ) from exc

    return ClassificationResponse(
        message="Clasificación de documento completada exitosamente",
        document_id=document_id,
        document_type=result.document_type.value if hasattr(result.document_type, "value") else str(result.document_type),
        confidence=result.confidence,
        matched_indicators=result.matched_indicators,
        scores=result.scores,
        detected_sections=result.detected_sections,
        reasons=result.reasons,
        is_definitive=result.is_definitive,
    )


@router.get(
    "/{document_id}/classification",
    response_model=ClassificationResponse,
    summary="Consultar resultado de clasificación del documento",
    dependencies=[require_permission("documents", "read")],
)
async def get_document_classification_endpoint(
    document_id: uuid.UUID,
    document_repo: DocumentRepo,
    storage: Storage,
) -> ClassificationResponse:
    """
    Retorna la clasificación del documento o la ejecuta si aún no se ha realizado.
    """
    doc = await document_repo.get_by_id(document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Documento con ID {document_id} no encontrado.",
        )

    use_case = ClassifyDocumentUseCase(
        document_repo=document_repo,
        storage_provider=storage,
    )
    result = await use_case.execute(document_id)

    return ClassificationResponse(
        message="Consulta de clasificación exitosa",
        document_id=document_id,
        document_type=result.document_type.value if hasattr(result.document_type, "value") else str(result.document_type),
        confidence=result.confidence,
        matched_indicators=result.matched_indicators,
        scores=result.scores,
        detected_sections=result.detected_sections,
        reasons=result.reasons,
        is_definitive=result.is_definitive,
    )


@router.post(
    "/{document_id}/extract-formato-unico",
    response_model=CanonicalResumeResponse,
    summary="Extraer datos estructurados de Formato Único DAFP",
    dependencies=[require_permission("documents", "write")],
)
async def extract_formato_unico_endpoint(
    document_id: uuid.UUID,
    document_repo: DocumentRepo,
    person_repo: PersonRepo,
    storage: Storage,
) -> CanonicalResumeResponse:
    """
    Ejecuta el extractor especializado de Formato Único sobre el documento,
    asociando o creando el registro de la persona, sus estudios, experiencia laboral,
    idiomas y trazabilidad por campo.
    """
    use_case = ExtractFormatoUnicoUseCase(
        document_repo=document_repo,
        person_repo=person_repo,
        storage_provider=storage,
    )
    try:
        resume = await use_case.execute(document_id)
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.message,
        ) from exc
    except Exception as exc:
        logger.error("formato_unico_extraction_failed", document_id=str(document_id), error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error durante la extracción de Formato Único: {exc}",
        ) from exc

    doc = await document_repo.get_by_id(document_id)
    resume_dict = resume.to_dict()

    return CanonicalResumeResponse(
        message="Extracción canónica completada exitosamente",
        document_id=document_id,
        person_id=doc.person_id if doc else None,
        person=CanonicalPersonResponse(**resume_dict["person"]),
        contact=CanonicalContactResponse(**resume_dict["contact"]),
        educations=[CanonicalEducationResponse(**e) for e in resume_dict["educations"]],
        work_experiences=[CanonicalWorkExperienceResponse(**w) for w in resume_dict["work_experiences"]],
        experience_summary=CanonicalExperienceSummaryResponse(**resume_dict["experience_summary"]) if resume_dict["experience_summary"] else None,
        languages=[CanonicalLanguageResponse(**l) for l in resume_dict["languages"]],
        extracted_fields_count=resume_dict["extracted_fields_count"],
    )


@router.post(
    "/{document_id}/extract-ats",
    response_model=CanonicalResumeResponse,
    summary="Extraer datos estructurados de hoja de vida en formato libre (ATS)",
    dependencies=[require_permission("documents", "write")],
)
async def extract_ats_endpoint(
    document_id: uuid.UUID,
    document_repo: DocumentRepo,
    person_repo: PersonRepo,
    storage: Storage,
) -> CanonicalResumeResponse:
    """
    Ejecuta el pipeline de extracción heurística ATS para hojas de vida abiertas
    en español e inglés, mapeando los resultados al modelo canónico común.
    """
    use_case = ExtractAtsResumeUseCase(
        document_repo=document_repo,
        person_repo=person_repo,
        storage_provider=storage,
    )
    try:
        resume = await use_case.execute(document_id)
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.message,
        ) from exc
    except Exception as exc:
        logger.error("ats_extraction_failed", document_id=str(document_id), error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error durante la extracción de hoja de vida ATS: {exc}",
        ) from exc

    doc = await document_repo.get_by_id(document_id)
    resume_dict = resume.to_dict()

    return CanonicalResumeResponse(
        message="Extracción ATS completada exitosamente",
        document_id=document_id,
        person_id=doc.person_id if doc else None,
        person=CanonicalPersonResponse(**resume_dict["person"]),
        contact=CanonicalContactResponse(**resume_dict["contact"]),
        educations=[CanonicalEducationResponse(**e) for e in resume_dict["educations"]],
        work_experiences=[CanonicalWorkExperienceResponse(**w) for w in resume_dict["work_experiences"]],
        experience_summary=CanonicalExperienceSummaryResponse(**resume_dict["experience_summary"]) if resume_dict["experience_summary"] else None,
        languages=[CanonicalLanguageResponse(**l) for l in resume_dict["languages"]],
        extracted_fields_count=resume_dict["extracted_fields_count"],
    )


@router.get(
    "/{document_id}/canonical-resume",
    response_model=CanonicalResumeResponse,
    summary="Consultar hoja de vida canónica extraída del documento",
    dependencies=[require_permission("documents", "read")],
)
async def get_canonical_resume_endpoint(
    document_id: uuid.UUID,
    document_repo: DocumentRepo,
    person_repo: PersonRepo,
    storage: Storage,
) -> CanonicalResumeResponse:
    """
    Retorna la información canónica estructurada asociada al documento.
    """
    doc = await document_repo.get_by_id(document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Documento con ID {document_id} no encontrado.",
        )

    get_use_case = GetCanonicalResumeUseCase(
        document_repo=document_repo,
        person_repo=person_repo,
    )
    person = await get_use_case.execute(document_id)

    if not person:
        # If extraction hasn't been run yet, ensure document is classified
        if not doc.document_type or doc.document_type == DocumentType.UNKNOWN.value:
            classify_use_case = ClassifyDocumentUseCase(
                document_repo=document_repo,
                storage_provider=storage,
            )
            try:
                cls_res = await classify_use_case.execute(document_id)
                doc = await document_repo.get_by_id(document_id) or doc
            except Exception as exc:
                logger.warning("auto_classification_in_canonical_failed", error=str(exc))

        if doc.document_type == DocumentType.ATS.value:
            ats_use_case = ExtractAtsResumeUseCase(
                document_repo=document_repo,
                person_repo=person_repo,
                storage_provider=storage,
            )
            resume = await ats_use_case.execute(document_id)
        else:
            extract_use_case = ExtractFormatoUnicoUseCase(
                document_repo=document_repo,
                person_repo=person_repo,
                storage_provider=storage,
            )
            resume = await extract_use_case.execute(document_id)
        doc = await document_repo.get_by_id(document_id)
        resume_dict = resume.to_dict()
        return CanonicalResumeResponse(
            message="Extracción canónica completada exitosamente",
            document_id=document_id,
            person_id=doc.person_id if doc else None,
            person=CanonicalPersonResponse(**resume_dict["person"]),
            contact=CanonicalContactResponse(**resume_dict["contact"]),
            educations=[CanonicalEducationResponse(**e) for e in resume_dict["educations"]],
            work_experiences=[CanonicalWorkExperienceResponse(**w) for w in resume_dict["work_experiences"]],
            experience_summary=CanonicalExperienceSummaryResponse(**resume_dict["experience_summary"]) if resume_dict["experience_summary"] else None,
            languages=[CanonicalLanguageResponse(**l) for l in resume_dict["languages"]],
            extracted_fields_count=resume_dict["extracted_fields_count"],
        )

    # Build response from saved person and relationships
    contact_dict = {
        "address": person.contact_information.address if person.contact_information else None,
        "country": person.contact_information.country if person.contact_information else None,
        "department": person.contact_information.department if person.contact_information else None,
        "municipality": person.contact_information.municipality if person.contact_information else None,
        "telephone": person.contact_information.telephone if person.contact_information else None,
        "mobile_phone": person.contact_information.mobile_phone if person.contact_information else None,
        "email": person.contact_information.email if person.contact_information else None,
    }

    # Determine professional card if any
    prof_card = person.military_card_number
    if not prof_card and person.educations:
        for edu in person.educations:
            if edu.professional_card_no:
                prof_card = edu.professional_card_no
                break

    prof_name = person.primary_profession.name if person.primary_profession else None
    cat_name = person.primary_category.name if person.primary_category else None
    headline = person.professional_profile.summary if person.professional_profile else None

    person_dict = {
        "identification_type": person.identification_type,
        "identification_number": person.identification_number,
        "first_surname": person.first_surname,
        "second_surname": person.second_surname,
        "first_name": person.first_name,
        "middle_name": person.middle_name,
        "full_name": f"{person.first_name or ''} {person.first_surname or ''}".strip(),
        "sex": person.sex,
        "nationality": person.nationality,
        "birth_date": person.birth_date.isoformat() if person.birth_date else None,
        "birth_country": person.birth_country,
        "birth_department": person.birth_department,
        "birth_municipality": person.birth_municipality,
        "military_card_number": person.military_card_number,
        "military_card_district": person.military_card_district,
        "military_card_class": person.military_card_class,
        "professional_card_number": prof_card,
        "headline": headline,
        "profession": prof_name,
        "category": cat_name,
    }

    educations_list = [
        CanonicalEducationResponse(
            level=e.level,
            institution=e.institution,
            program=e.program,
            academic_modality=e.academic_modality,
            semesters_count=e.semesters_count,
            graduation_status=e.graduation_status,
            degree_title=e.degree_title,
            professional_card_no=e.professional_card_no,
            completion_month=e.completion_month,
            completion_year=e.completion_year,
            country=e.country,
            department=e.department,
            municipality=e.municipality,
            source_page=e.source_page,
        )
        for e in (person.educations or [])
    ]

    experiences_list = []
    for w in (person.work_experiences or []):
        tot_m = 0
        if w.start_date:
            end_d = date.today() if w.is_current else (w.end_date or date.today())
            if end_d >= w.start_date:
                diff_years = end_d.year - w.start_date.year
                diff_months = end_d.month - w.start_date.month
                tot_m = diff_years * 12 + diff_months
                if tot_m == 0 and end_d.year == w.start_date.year:
                    tot_m = 12
                tot_m = max(1, tot_m)

        experiences_list.append(
            CanonicalWorkExperienceResponse(
                company_name=w.company_name,
                sector=w.sector,
                position=w.position,
                department_unit=w.department_unit,
                country=w.country,
                department=w.department,
                municipality=w.municipality,
                address=w.address,
                telephone=w.telephone,
                entity_email=w.entity_email,
                start_date=w.start_date.isoformat() if w.start_date else None,
                end_date=w.end_date.isoformat() if w.end_date else None,
                is_current=w.is_current,
                responsibilities=w.responsibilities,
                source_page=w.source_page,
                total_months=tot_m,
                is_public_sector=(w.sector == "PUBLIC"),
            )
        )

    summary_resp = None
    if person.experience_summary:
        summary_resp = CanonicalExperienceSummaryResponse(
            public_years=person.experience_summary.public_years,
            public_months=person.experience_summary.public_months,
            private_years=person.experience_summary.private_years,
            private_months=person.experience_summary.private_months,
            independent_years=person.experience_summary.independent_years,
            independent_months=person.experience_summary.independent_months,
            total_years=person.experience_summary.total_years,
            total_months=person.experience_summary.total_months,
        )

    languages_list = [
        CanonicalLanguageResponse(
            language_name=l.language_name,
            speaking=l.speaking,
            reading=l.reading,
            writing=l.writing,
            source_page=l.source_page,
        )
        for l in (person.languages or [])
    ]

    return CanonicalResumeResponse(
        message="Consulta de hoja de vida canónica exitosa",
        document_id=document_id,
        person_id=person.id,
        person=CanonicalPersonResponse(**person_dict),
        contact=CanonicalContactResponse(**contact_dict),
        educations=educations_list,
        work_experiences=experiences_list,
        experience_summary=summary_resp,
        languages=languages_list,
        extracted_fields_count=len(educations_list) + len(experiences_list),
    )


