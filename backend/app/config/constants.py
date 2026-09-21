"""
Application-wide constants.

These are fixed values that do not change per environment.
Business rules that can vary should live in settings.py instead.
"""

from enum import StrEnum


# ============================================================
# Document Types
# ============================================================

class DocumentType(StrEnum):
    FORMATO_UNICO = "FORMATO_UNICO"
    ATS = "ATS"
    UNKNOWN = "UNKNOWN"


# ============================================================
# Processing Job States
# ============================================================

class JobStatus(StrEnum):
    UPLOADED = "UPLOADED"
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    OCR_COMPLETED = "OCR_COMPLETED"
    EXTRACTING = "EXTRACTING"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


# ============================================================
# Review / Extraction Field States
# ============================================================

class ReviewStatus(StrEnum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    CORRECTED = "CORRECTED"
    REJECTED = "REJECTED"


# ============================================================
# Confidence Levels
# ============================================================

class ConfidenceLevel(StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


# ============================================================
# User Roles
# ============================================================

class UserRole(StrEnum):
    ADMIN = "ADMIN"
    DIRECTOR = "DIRECTOR"
    GESTOR = "GESTOR"
    CONSULTOR = "CONSULTOR"


# ============================================================
# Academic Levels
# ============================================================

class AcademicLevel(StrEnum):
    BASIC = "BASIC"
    SECONDARY = "SECONDARY"
    HIGH_SCHOOL = "HIGH_SCHOOL"
    TECHNICAL = "TECHNICAL"
    TECHNOLOGIST = "TECHNOLOGIST"
    UNDERGRADUATE = "UNDERGRADUATE"
    SPECIALIZATION = "SPECIALIZATION"
    MASTER = "MASTER"
    DOCTORATE = "DOCTORATE"
    OTHER = "OTHER"


# ============================================================
# Graduation Status
# ============================================================

class GraduationStatus(StrEnum):
    GRADUATED = "GRADUATED"
    IN_PROGRESS = "IN_PROGRESS"
    INCOMPLETE = "INCOMPLETE"


# ============================================================
# Work Sectors
# ============================================================

class WorkSector(StrEnum):
    PUBLIC = "PUBLIC"
    PRIVATE = "PRIVATE"
    INDEPENDENT = "INDEPENDENT"


# ============================================================
# Language Proficiency Levels
# ============================================================

class LanguageProficiency(StrEnum):
    BASIC = "BASIC"
    INTERMEDIATE = "INTERMEDIATE"
    ADVANCED = "ADVANCED"
    NATIVE = "NATIVE"


# ============================================================
# Identification Types (Colombia-specific)
# ============================================================

class IdentificationType(StrEnum):
    CC = "CC"    # Cédula de Ciudadanía
    CE = "CE"    # Cédula de Extranjería
    PA = "PA"    # Pasaporte
    NIT = "NIT"  # NIT
    TI = "TI"    # Tarjeta de Identidad
    RC = "RC"    # Registro Civil
    PE = "PE"    # Permiso Especial de Permanencia
    PPT = "PPT"  # Permiso de Protección Temporal
    OTHER = "OTHER"


# ============================================================
# OCR Providers
# ============================================================

class OCRProvider(StrEnum):
    NATIVE = "NATIVE"       # PyMuPDF native text extraction
    GOOGLE_DAI = "GOOGLE_DAI"
    AZURE_DI = "AZURE_DI"
    MOCK = "MOCK"


# ============================================================
# Audit Actions
# ============================================================

class AuditAction(StrEnum):
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    FAILED_LOGIN = "FAILED_LOGIN"
    ACCOUNT_LOCKED = "ACCOUNT_LOCKED"
    PASSWORD_CHANGED = "PASSWORD_CHANGED"
    UPLOAD_DOCUMENT = "UPLOAD_DOCUMENT"
    DELETE_DOCUMENT = "DELETE_DOCUMENT"
    PROCESS_DOCUMENT = "PROCESS_DOCUMENT"
    VIEW_DOCUMENT = "VIEW_DOCUMENT"
    EDIT_EXTRACTED_FIELD = "EDIT_EXTRACTED_FIELD"
    CONFIRM_EXTRACTION = "CONFIRM_EXTRACTION"
    CREATE_USER = "CREATE_USER"
    MODIFY_USER = "MODIFY_USER"
    DEACTIVATE_USER = "DEACTIVATE_USER"
    CHANGE_ROLE = "CHANGE_ROLE"
    EXPORT_REPORT = "EXPORT_REPORT"
    VIEW_SENSITIVE_DOCUMENT = "VIEW_SENSITIVE_DOCUMENT"


# ============================================================
# Permissions (resource:action format)
# ============================================================

PERMISSIONS: dict[str, list[str]] = {
    "documents": ["read", "write", "delete"],
    "persons": ["read", "write"],
    "extractions": ["read", "review"],
    "reports": ["read", "export"],
    "users": ["manage"],
    "audit_logs": ["read"],
    "system": ["admin"],
}

# Default permissions per role
ROLE_PERMISSIONS: dict[str, list[str]] = {
    "ADMIN": [
        "documents:read", "documents:write", "documents:delete",
        "persons:read", "persons:write",
        "extractions:read", "extractions:review",
        "reports:read", "reports:export",
        "users:manage",
        "audit_logs:read",
        "system:admin",
    ],
    "DIRECTOR": [
        "documents:read",
        "persons:read",
        "extractions:read",
        "reports:read", "reports:export",
        "audit_logs:read",
    ],
    "GESTOR": [
        "documents:read", "documents:write",
        "persons:read",
        "extractions:read", "extractions:review",
        "reports:read",
    ],
    "CONSULTOR": [
        "documents:read",
        "persons:read",
        "reports:read",
    ],
}

# ============================================================
# Processing constants
# ============================================================

MAX_PDF_PAGES = 200          # Reject PDFs with more pages than this
MIN_TEXT_CHARS_PER_PAGE = 50  # Below this → consider page as image-only
PDF_MAGIC_BYTES = b"%PDF"    # First bytes of a valid PDF

# Pipeline step names (for logging and tracking)
PIPELINE_STEPS = [
    "ingestion",
    "text_extraction",
    "ocr",
    "layout_analysis",
    "classification",
    "data_extraction",
    "normalization",
    "validation",
    "confidence_evaluation",
    "persistence",
]
