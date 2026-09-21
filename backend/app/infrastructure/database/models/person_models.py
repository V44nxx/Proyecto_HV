"""
ORM models: persons, contact_information, professional_categories, professions.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    ARRAY,
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import (
    Base,
    SoftDeleteMixin,
    StringArray,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class ProfessionalCategory(Base, UUIDPrimaryKeyMixin):
    """High-level professional grouping: Engineering, Medicine, Law, etc."""

    __tablename__ = "professional_categories"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    professions: Mapped[list["Profession"]] = relationship(
        "Profession", back_populates="category"
    )

    def __repr__(self) -> str:
        return f"<ProfessionalCategory name={self.name}>"


class Profession(Base, UUIDPrimaryKeyMixin):
    """
    Specific professions linked to a category.
    aliases stores equivalent names for normalization (e.g. ['Ing. Sistemas', 'Systems Engineer']).
    """

    __tablename__ = "professions"

    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("professional_categories.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    aliases: Mapped[list[str] | None] = mapped_column(StringArray, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    category: Mapped["ProfessionalCategory"] = relationship(
        "ProfessionalCategory", back_populates="professions"
    )
    persons: Mapped[list["Person"]] = relationship(
        "Person", back_populates="primary_profession", foreign_keys="Person.primary_profession_id"
    )

    def __repr__(self) -> str:
        return f"<Profession name={self.name}>"


class Person(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """
    Core entity: a natural person extracted from one or more resumes.

    identification_type + identification_number must be unique
    (enforced by unique constraint, not application logic alone).
    """

    __tablename__ = "persons"

    # ---- Identification ----
    identification_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    identification_number: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # ---- Name ----
    first_surname: Mapped[str | None] = mapped_column(String(100), nullable=True)
    second_surname: Mapped[str | None] = mapped_column(String(100), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    middle_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # ---- Demographics ----
    sex: Mapped[str | None] = mapped_column(String(20), nullable=True)
    nationality: Mapped[str | None] = mapped_column(String(100), nullable=True)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    birth_country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    birth_department: Mapped[str | None] = mapped_column(String(100), nullable=True)
    birth_municipality: Mapped[str | None] = mapped_column(String(150), nullable=True)

    # ---- Military (Formato Único) ----
    military_card_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    military_card_district: Mapped[str | None] = mapped_column(String(100), nullable=True)
    military_card_class: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # ---- Professional Classification ----
    primary_profession_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("professions.id"),
        nullable=True,
    )
    primary_category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("professional_categories.id"),
        nullable=True,
    )

    # ---- Audit ----
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    # ---- Constraints ----
    __table_args__ = (
        UniqueConstraint(
            "identification_type",
            "identification_number",
            name="uq_person_identification",
        ),
    )

    # ---- Relationships ----
    primary_profession: Mapped["Profession | None"] = relationship(
        "Profession", back_populates="persons", foreign_keys=[primary_profession_id]
    )
    contact_information: Mapped["ContactInformation | None"] = relationship(
        "ContactInformation", back_populates="person", uselist=False, cascade="all, delete-orphan"
    )
    documents: Mapped[list["Document"]] = relationship(
        "Document", back_populates="person"
    )
    educations: Mapped[list["Education"]] = relationship(
        "Education", back_populates="person", cascade="all, delete-orphan"
    )
    work_experiences: Mapped[list["WorkExperience"]] = relationship(
        "WorkExperience", back_populates="person", cascade="all, delete-orphan"
    )
    experience_summary: Mapped["ExperienceSummary | None"] = relationship(
        "ExperienceSummary", back_populates="person", uselist=False, cascade="all, delete-orphan"
    )
    languages: Mapped[list["Language"]] = relationship(
        "Language", back_populates="person", cascade="all, delete-orphan"
    )
    certifications: Mapped[list["Certification"]] = relationship(
        "Certification", back_populates="person", cascade="all, delete-orphan"
    )
    professional_profile: Mapped["ProfessionalProfile | None"] = relationship(
        "ProfessionalProfile", back_populates="person", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"<Person {self.first_name} {self.first_surname} "
            f"id={self.identification_number}>"
        )


class ContactInformation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Contact details linked to a person."""

    __tablename__ = "contact_information"

    person_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("persons.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    department: Mapped[str | None] = mapped_column(String(100), nullable=True)
    municipality: Mapped[str | None] = mapped_column(String(150), nullable=True)
    telephone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    mobile_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    person: Mapped["Person"] = relationship("Person", back_populates="contact_information")
