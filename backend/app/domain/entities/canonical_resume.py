"""
Canonical resume domain entities and value objects.
Common normalized representation for all resume formats (Formato Único and ATS).
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Any


@dataclass
class CanonicalPerson:
    """Personal identity and demographic data."""
    identification_type: str | None = None
    identification_number: str | None = None
    first_surname: str | None = None
    second_surname: str | None = None
    first_name: str | None = None
    middle_name: str | None = None
    sex: str | None = None
    nationality: str | None = None
    birth_date: date | None = None
    birth_country: str | None = None
    birth_department: str | None = None
    birth_municipality: str | None = None
    military_card_number: str | None = None
    military_card_district: str | None = None
    military_card_class: str | None = None

    @property
    def full_name(self) -> str:
        parts = [self.first_name, self.middle_name, self.first_surname, self.second_surname]
        return " ".join(p for p in parts if p)


@dataclass
class CanonicalContact:
    """Contact details and location."""
    address: str | None = None
    country: str | None = None
    department: str | None = None
    municipality: str | None = None
    telephone: str | None = None
    mobile_phone: str | None = None
    email: str | None = None


@dataclass
class CanonicalEducation:
    """Educational qualification record."""
    level: str  # BASIC, SECONDARY, HIGH_SCHOOL, UNDERGRADUATE, SPECIALIZATION, MASTER, DOCTORATE, etc.
    institution: str | None = None
    program: str | None = None
    academic_modality: str | None = None
    semesters_count: int | None = None
    graduation_status: str | None = None  # GRADUATED, IN_PROGRESS, INCOMPLETE
    degree_title: str | None = None
    professional_card_no: str | None = None
    completion_month: int | None = None
    completion_year: int | None = None
    country: str | None = None
    department: str | None = None
    municipality: str | None = None
    source_page: int | None = None


@dataclass
class CanonicalWorkExperience:
    """Employment / contractual experience record."""
    company_name: str | None = None
    sector: str | None = None  # PUBLIC, PRIVATE, INDEPENDENT
    position: str | None = None
    department_unit: str | None = None
    country: str | None = None
    department: str | None = None
    municipality: str | None = None
    address: str | None = None
    telephone: str | None = None
    entity_email: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    is_current: bool = False
    responsibilities: str | None = None
    source_page: int | None = None


@dataclass
class CanonicalExperienceSummary:
    """Cumulative professional experience totals (Formato Único)."""
    public_years: int = 0
    public_months: int = 0
    private_years: int = 0
    private_months: int = 0
    independent_years: int = 0
    independent_months: int = 0
    total_years: int = 0
    total_months: int = 0


@dataclass
class CanonicalLanguage:
    """Language proficiency record."""
    language_name: str
    speaking: str | None = None  # REGULAR, BIEN, MUY_BIEN
    reading: str | None = None
    writing: str | None = None
    source_page: int | None = None


@dataclass
class ExtractedFieldItem:
    """Traceability metadata for an individual extracted data point."""
    field_name: str
    raw_value: str | None = None
    normalized_value: str | None = None
    page_number: int = 1
    bounding_box: dict[str, float] | None = None
    confidence: float = 0.95


@dataclass
class CanonicalResume:
    """
    Root aggregate representing a complete normalized resume.
    """
    person: CanonicalPerson = field(default_factory=CanonicalPerson)
    contact: CanonicalContact = field(default_factory=CanonicalContact)
    educations: list[CanonicalEducation] = field(default_factory=list)
    work_experiences: list[CanonicalWorkExperience] = field(default_factory=list)
    experience_summary: CanonicalExperienceSummary | None = None
    languages: list[CanonicalLanguage] = field(default_factory=list)
    extracted_fields: list[ExtractedFieldItem] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize complete canonical resume to dictionary."""
        return {
            "person": {
                "identification_type": self.person.identification_type,
                "identification_number": self.person.identification_number,
                "first_surname": self.person.first_surname,
                "second_surname": self.person.second_surname,
                "first_name": self.person.first_name,
                "middle_name": self.person.middle_name,
                "full_name": self.person.full_name,
                "sex": self.person.sex,
                "nationality": self.person.nationality,
                "birth_date": self.person.birth_date.isoformat() if self.person.birth_date else None,
                "birth_country": self.person.birth_country,
                "birth_department": self.person.birth_department,
                "birth_municipality": self.person.birth_municipality,
                "military_card_number": self.person.military_card_number,
                "military_card_district": self.person.military_card_district,
                "military_card_class": self.person.military_card_class,
            },
            "contact": {
                "address": self.contact.address,
                "country": self.contact.country,
                "department": self.contact.department,
                "municipality": self.contact.municipality,
                "telephone": self.contact.telephone,
                "mobile_phone": self.contact.mobile_phone,
                "email": self.contact.email,
            },
            "educations": [
                {
                    "level": e.level,
                    "institution": e.institution,
                    "program": e.program,
                    "academic_modality": e.academic_modality,
                    "semesters_count": e.semesters_count,
                    "graduation_status": e.graduation_status,
                    "degree_title": e.degree_title,
                    "professional_card_no": e.professional_card_no,
                    "completion_month": e.completion_month,
                    "completion_year": e.completion_year,
                    "country": e.country,
                    "department": e.department,
                    "municipality": e.municipality,
                    "source_page": e.source_page,
                }
                for e in self.educations
            ],
            "work_experiences": [
                {
                    "company_name": w.company_name,
                    "sector": w.sector,
                    "position": w.position,
                    "department_unit": w.department_unit,
                    "country": w.country,
                    "department": w.department,
                    "municipality": w.municipality,
                    "address": w.address,
                    "telephone": w.telephone,
                    "entity_email": w.entity_email,
                    "start_date": w.start_date.isoformat() if w.start_date else None,
                    "end_date": w.end_date.isoformat() if w.end_date else None,
                    "is_current": w.is_current,
                    "responsibilities": w.responsibilities,
                    "source_page": w.source_page,
                }
                for w in self.work_experiences
            ],
            "experience_summary": {
                "public_years": self.experience_summary.public_years,
                "public_months": self.experience_summary.public_months,
                "private_years": self.experience_summary.private_years,
                "private_months": self.experience_summary.private_months,
                "independent_years": self.experience_summary.independent_years,
                "independent_months": self.experience_summary.independent_months,
                "total_years": self.experience_summary.total_years,
                "total_months": self.experience_summary.total_months,
            }
            if self.experience_summary
            else None,
            "languages": [
                {
                    "language_name": l.language_name,
                    "speaking": l.speaking,
                    "reading": l.reading,
                    "writing": l.writing,
                    "source_page": l.source_page,
                }
                for l in self.languages
            ],
            "extracted_fields_count": len(self.extracted_fields),
            "metadata": self.metadata,
        }
