"""
Models package: exposes all ORM models for Alembic autogenerate.

Import order matters for relationship resolution.
"""

from app.infrastructure.database.base import Base
from app.infrastructure.database.models.user_models import (
    AuditLog,
    Permission,
    Role,
    RolePermission,
    User,
)
from app.infrastructure.database.models.person_models import (
    ContactInformation,
    Person,
    ProfessionalCategory,
    Profession,
)
from app.infrastructure.database.models.document_models import (
    Document,
    DocumentExtraction,
    DocumentPage,
    ExtractedField,
    ProcessingJob,
)
from app.infrastructure.database.models.resume_models import (
    Certification,
    Education,
    ExperienceSummary,
    Language,
    ProfessionalProfile,
    WorkExperience,
)

__all__ = [
    "Base",
    # Users / Auth
    "Role",
    "Permission",
    "RolePermission",
    "User",
    "AuditLog",
    # Persons
    "ProfessionalCategory",
    "Profession",
    "Person",
    "ContactInformation",
    # Documents
    "Document",
    "DocumentPage",
    "DocumentExtraction",
    "ExtractedField",
    "ProcessingJob",
    # Resume data
    "Education",
    "WorkExperience",
    "ExperienceSummary",
    "Language",
    "Certification",
    "ProfessionalProfile",
]
