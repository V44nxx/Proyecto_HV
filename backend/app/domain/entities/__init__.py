"""
Domain entities package.
"""

from app.domain.entities.canonical_resume import (
    CanonicalContact,
    CanonicalEducation,
    CanonicalExperienceSummary,
    CanonicalLanguage,
    CanonicalPerson,
    CanonicalResume,
    CanonicalWorkExperience,
    ExtractedFieldItem,
)

__all__ = [
    "CanonicalPerson",
    "CanonicalContact",
    "CanonicalEducation",
    "CanonicalWorkExperience",
    "CanonicalExperienceSummary",
    "CanonicalLanguage",
    "ExtractedFieldItem",
    "CanonicalResume",
]
