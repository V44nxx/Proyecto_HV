"""
ORM models: educations, work_experiences, experience_summary,
languages, certifications, professional_profiles.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    ARRAY,
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import (
    Base,
    StringArray,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    utcnow,
)


class Education(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Academic formation record for a person.
    Each degree/level is stored as a separate record.
    """

    __tablename__ = "educations"

    person_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("persons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    level: Mapped[str] = mapped_column(String(50), nullable=False)
    # BASIC | SECONDARY | HIGH_SCHOOL | TECHNICAL | TECHNOLOGIST |
    # UNDERGRADUATE | SPECIALIZATION | MASTER | DOCTORATE | OTHER

    institution: Mapped[str | None] = mapped_column(String(255), nullable=True)
    program: Mapped[str | None] = mapped_column(String(255), nullable=True)
    academic_modality: Mapped[str | None] = mapped_column(String(100), nullable=True)
    semesters_count: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    graduation_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # GRADUATED | IN_PROGRESS | INCOMPLETE

    degree_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    professional_card_no: Mapped[str | None] = mapped_column(String(100), nullable=True)
    completion_month: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    completion_year: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)

    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    department: Mapped[str | None] = mapped_column(String(100), nullable=True)
    municipality: Mapped[str | None] = mapped_column(String(150), nullable=True)

    # ---- Traceability ----
    source_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_field_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("extracted_fields.id"),
        nullable=True,
    )

    __table_args__ = (
        CheckConstraint(
            "completion_month IS NULL OR (completion_month >= 1 AND completion_month <= 12)",
            name="chk_education_month",
        ),
    )

    person: Mapped["Person"] = relationship("Person", back_populates="educations")

    def __repr__(self) -> str:
        return f"<Education person={self.person_id} level={self.level} institution={self.institution}>"


class WorkExperience(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    A single job/position for a person.
    Each employer = separate record for normalization and searchability.
    """

    __tablename__ = "work_experiences"

    person_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("persons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    company_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sector: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # PUBLIC | PRIVATE | INDEPENDENT

    position: Mapped[str | None] = mapped_column(String(255), nullable=True)
    department_unit: Mapped[str | None] = mapped_column(String(255), nullable=True)

    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    department: Mapped[str | None] = mapped_column(String(100), nullable=True)
    municipality: Mapped[str | None] = mapped_column(String(150), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    telephone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    entity_email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    responsibilities: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ---- Traceability ----
    source_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_field_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("extracted_fields.id"),
        nullable=True,
    )

    person: Mapped["Person"] = relationship("Person", back_populates="work_experiences")

    def __repr__(self) -> str:
        return f"<WorkExperience person={self.person_id} company={self.company_name}>"


class ExperienceSummary(Base, UUIDPrimaryKeyMixin):
    """
    Aggregated experience totals from the Formato Único.
    One record per person.
    """

    __tablename__ = "experience_summary"

    person_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("persons.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    public_years: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    public_months: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    private_years: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    private_months: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    independent_years: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    independent_months: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    total_years: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    total_months: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)

    updated_at: Mapped[datetime] = mapped_column(
        __import__("sqlalchemy").DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        server_default=__import__("sqlalchemy").text("NOW()"),
        nullable=False,
    )

    person: Mapped["Person"] = relationship("Person", back_populates="experience_summary")

    def __repr__(self) -> str:
        return f"<ExperienceSummary person={self.person_id} total={self.total_years}y{self.total_months}m>"


class Language(Base, UUIDPrimaryKeyMixin):
    """Language skill record for a person."""

    __tablename__ = "languages"

    person_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("persons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    language_name: Mapped[str] = mapped_column(String(100), nullable=False)
    speaking: Mapped[str | None] = mapped_column(String(20), nullable=True)
    reading: Mapped[str | None] = mapped_column(String(20), nullable=True)
    writing: Mapped[str | None] = mapped_column(String(20), nullable=True)

    source_page: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        __import__("sqlalchemy").DateTime(timezone=True),
        default=utcnow,
        server_default=__import__("sqlalchemy").text("NOW()"),
        nullable=False,
    )

    person: Mapped["Person"] = relationship("Person", back_populates="languages")

    def __repr__(self) -> str:
        return f"<Language person={self.person_id} language={self.language_name}>"


class Certification(Base, UUIDPrimaryKeyMixin):
    """A certification, course, or continuing education credential."""

    __tablename__ = "certifications"

    person_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("persons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    issuing_entity: Mapped[str | None] = mapped_column(String(255), nullable=True)
    issue_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    credential_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    source_page: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        __import__("sqlalchemy").DateTime(timezone=True),
        default=utcnow,
        server_default=__import__("sqlalchemy").text("NOW()"),
        nullable=False,
    )

    person: Mapped["Person"] = relationship("Person", back_populates="certifications")

    def __repr__(self) -> str:
        return f"<Certification person={self.person_id} name={self.name}>"


class ProfessionalProfile(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Professional summary and skills (primarily from ATS resumes).
    One record per person.
    """

    __tablename__ = "professional_profiles"

    person_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("persons.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    skills: Mapped[list[str] | None] = mapped_column(StringArray, nullable=True)

    source_page: Mapped[int | None] = mapped_column(Integer, nullable=True)

    person: Mapped["Person"] = relationship("Person", back_populates="professional_profile")

    def __repr__(self) -> str:
        return f"<ProfessionalProfile person={self.person_id}>"
