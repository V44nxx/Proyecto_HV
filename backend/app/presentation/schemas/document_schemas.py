"""
Pydantic schemas for document endpoints.
"""

from datetime import datetime
import uuid

from pydantic import BaseModel, ConfigDict, Field


class DocumentResponse(BaseModel):
    """Public representation of a Document."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    person_id: uuid.UUID | None = None
    storage_key: str
    original_filename: str
    file_size_bytes: int
    mime_type: str
    checksum_sha256: str
    page_count: int | None = None
    document_type: str
    uploaded_by: uuid.UUID
    created_at: datetime
    updated_at: datetime


class ProcessingJobResponse(BaseModel):
    """Status and tracking details of an asynchronous processing job."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    status: str
    queue_name: str | None = None
    worker_id: str | None = None
    current_step: str | None = None
    progress_pct: int = 0
    error_message: str | None = None
    error_type: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime


class DocumentUploadResponse(BaseModel):
    """Response returned upon successful document upload."""

    message: str = "Documento subido exitosamente para procesamiento"
    document: DocumentResponse
    job: ProcessingJobResponse


class DocumentDetailResponse(BaseModel):
    """Full detail of a document including its latest processing job."""

    document: DocumentResponse
    latest_job: ProcessingJobResponse | None = None


class DocumentListResponse(BaseModel):
    """Paginated list of documents."""

    items: list[DocumentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class DocumentExtractionResponse(BaseModel):
    """Extraction record for a document or page."""

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: uuid.UUID
    document_id: uuid.UUID
    page_id: uuid.UUID | None = None
    ocr_provider: str | None = None
    raw_text: str | None = None
    confidence: float | None = None
    processing_ms: int | None = None
    model_version: str | None = None
    extracted_at: datetime


class ProcessTextResponse(BaseModel):
    """Response returned after running native text extraction / OCR."""

    message: str = "Extracción de texto completada exitosamente"
    document_id: uuid.UUID
    provider: str
    pages_count: int
    overall_confidence: float
    processing_ms: int
    full_text_preview: str


class ClassificationResponse(BaseModel):
    """Response returned upon classifying a document format."""

    message: str = "Clasificación de documento completada exitosamente"
    document_id: uuid.UUID
    document_type: str
    confidence: float
    matched_indicators: list[str] = Field(default_factory=list)
    scores: dict[str, float] = Field(default_factory=dict)
    detected_sections: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    is_definitive: bool


class CanonicalPersonResponse(BaseModel):
    """Normalized person identity and demographic data."""

    identification_type: str | None = None
    identification_number: str | None = None
    first_surname: str | None = None
    second_surname: str | None = None
    first_name: str | None = None
    middle_name: str | None = None
    full_name: str | None = None
    sex: str | None = None
    nationality: str | None = None
    birth_date: str | None = None
    birth_country: str | None = None
    birth_department: str | None = None
    birth_municipality: str | None = None
    military_card_number: str | None = None
    military_card_district: str | None = None
    military_card_class: str | None = None


class CanonicalContactResponse(BaseModel):
    """Contact information response."""

    address: str | None = None
    country: str | None = None
    department: str | None = None
    municipality: str | None = None
    telephone: str | None = None
    mobile_phone: str | None = None
    email: str | None = None


class CanonicalEducationResponse(BaseModel):
    """Education record response."""

    level: str
    institution: str | None = None
    program: str | None = None
    academic_modality: str | None = None
    semesters_count: int | None = None
    graduation_status: str | None = None
    degree_title: str | None = None
    professional_card_no: str | None = None
    completion_month: int | None = None
    completion_year: int | None = None
    country: str | None = None
    department: str | None = None
    municipality: str | None = None
    source_page: int | None = None


class CanonicalWorkExperienceResponse(BaseModel):
    """Work experience record response."""

    company_name: str | None = None
    sector: str | None = None
    position: str | None = None
    department_unit: str | None = None
    country: str | None = None
    department: str | None = None
    municipality: str | None = None
    address: str | None = None
    telephone: str | None = None
    entity_email: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    is_current: bool = False
    responsibilities: str | None = None
    source_page: int | None = None


class CanonicalExperienceSummaryResponse(BaseModel):
    """Experience summary response."""

    public_years: int = 0
    public_months: int = 0
    private_years: int = 0
    private_months: int = 0
    independent_years: int = 0
    independent_months: int = 0
    total_years: int = 0
    total_months: int = 0


class CanonicalLanguageResponse(BaseModel):
    """Language record response."""

    language_name: str
    speaking: str | None = None
    reading: str | None = None
    writing: str | None = None
    source_page: int | None = None


class CanonicalResumeResponse(BaseModel):
    """Full canonical resume response."""

    message: str = "Extracción canónica completada exitosamente"
    document_id: uuid.UUID
    person_id: uuid.UUID | None = None
    person: CanonicalPersonResponse
    contact: CanonicalContactResponse
    educations: list[CanonicalEducationResponse] = Field(default_factory=list)
    work_experiences: list[CanonicalWorkExperienceResponse] = Field(default_factory=list)
    experience_summary: CanonicalExperienceSummaryResponse | None = None
    languages: list[CanonicalLanguageResponse] = Field(default_factory=list)
    extracted_fields_count: int = 0


