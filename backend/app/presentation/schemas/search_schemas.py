"""
Pydantic v2 schemas for Advanced Search and Candidate Dossier.
"""

from datetime import date, datetime
from typing import Any
import uuid
from pydantic import BaseModel, ConfigDict, Field


class CandidateSummaryItem(BaseModel):
    """Summarized candidate profile returned in search results."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    identification_type: str | None = None
    identification_number: str | None = None
    first_name: str | None = None
    middle_name: str | None = None
    first_surname: str | None = None
    second_surname: str | None = None
    full_name: str
    primary_profession: str | None = None
    profession_name: str | None = None
    primary_category: str | None = None
    category_name: str | None = None
    email: str | None = None
    telephone: str | None = None
    municipality: str | None = None
    department: str | None = None
    total_experience_years: int = 0
    top_education: str | None = None
    highest_academic_level: str | None = None
    skills: list[str] = Field(default_factory=list)
    documents_count: int = 0
    document_count: int = 0
    created_at: datetime


class CandidateSearchResponse(BaseModel):
    """Paginated search response with navigation metadata."""
    items: list[CandidateSummaryItem]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool


class ProfessionOption(BaseModel):
    """Profession item for UI filter dropdowns."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    category_id: uuid.UUID | None = None
    aliases: list[str] | None = None


class CategoryOption(BaseModel):
    """Professional category with its linked professions."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    code: str | None = None
    description: str | None = None
    professions: list[ProfessionOption] = Field(default_factory=list)


class FilterOptionsResponse(BaseModel):
    """Available options for frontend filter selectors."""
    categories: list[CategoryOption]
    professions: list[ProfessionOption] = Field(default_factory=list)
    academic_levels: list[str]
    departments: list[str]


class SearchFacetsResponse(BaseModel):
    """Aggregation metrics across candidates."""
    total_candidates: int
    by_category: dict[str, int]
    by_profession: dict[str, int]
    by_academic_level: dict[str, int]
    by_department: dict[str, int]


class CandidateFullDetailResponse(BaseModel):
    """Comprehensive candidate dossier with all relational details."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    identification_type: str | None = None
    identification_number: str | None = None
    first_surname: str | None = None
    second_surname: str | None = None
    first_name: str | None = None
    middle_name: str | None = None
    full_name: str
    sex: str | None = None
    nationality: str | None = None
    birth_date: date | None = None
    birth_country: str | None = None
    birth_department: str | None = None
    birth_municipality: str | None = None
    military_card_number: str | None = None
    primary_profession: str | None = None
    profession_name: str | None = None
    primary_category: str | None = None
    category_name: str | None = None

    # Relational entities
    contact: dict[str, Any] | None = None
    educations: list[dict[str, Any]] = Field(default_factory=list)
    work_experiences: list[dict[str, Any]] = Field(default_factory=list)
    experience_summary: dict[str, Any] | None = None
    languages: list[dict[str, Any]] = Field(default_factory=list)
    certifications: list[dict[str, Any]] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    professional_summary: str | None = None
    documents: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime


class ClassifyProfessionResponse(BaseModel):
    """Result of auto-classifying a candidate's profession."""
    person_id: uuid.UUID
    category_name: str
    profession_name: str
    confidence: float
    applied: bool
