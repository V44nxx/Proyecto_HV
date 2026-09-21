"""
Formato Único (DAFP - Persona Natural) extractor.

Extracts structured personal, academic, and professional experience data
according to the standardized Colombian government resume template.
"""

from datetime import date, datetime
import re
from typing import Any

import structlog

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

logger = structlog.get_logger(__name__)


class FormatoUnicoExtractor:
    """
    Parser for Colombian Formato Único DAFP resumes.
    """

    MONTH_MAP = {
        "ENERO": 1, "ENE": 1,
        "FEBRERO": 2, "FEB": 2,
        "MARZO": 3, "MAR": 3,
        "ABRIL": 4, "ABR": 4,
        "MAYO": 5, "MAY": 5,
        "JUNIO": 6, "JUN": 6,
        "JULIO": 7, "JUL": 7,
        "AGOSTO": 8, "AGO": 8,
        "SEPTIEMBRE": 9, "SEP": 9, "SET": 9,
        "OCTUBRE": 10, "OCT": 10,
        "NOVIEMBRE": 11, "NOV": 11,
        "DICIEMBRE": 12, "DIC": 12,
    }

    @staticmethod
    def parse_date(date_str: str | None) -> date | None:
        """Parse various Colombian date formats into date object."""
        if not date_str:
            return None
        cleaned = re.sub(r"[^\w\/\-]", " ", date_str).strip()

        # 1. Standard DD/MM/YYYY or DD-MM-YYYY
        m = re.search(r"(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})", cleaned)
        if m:
            day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
            try:
                return date(year, month, day)
            except ValueError:
                pass

        # 2. YYYY-MM-DD or YYYY/MM/DD
        m = re.search(r"(\d{4})[\/\-](\d{1,2})[\/\-](\d{1,2})", cleaned)
        if m:
            year, month, day = int(m.group(1)), int(m.group(2)), int(m.group(3))
            try:
                return date(year, month, day)
            except ValueError:
                pass

        # 3. DD de [Mes] de YYYY
        m = re.search(r"(\d{1,2})\s+DE\s+([A-Za-z]+)\s+DE\s+(\d{4})", cleaned.upper())
        if m:
            day = int(m.group(1))
            month_name = m.group(2)
            year = int(m.group(3))
            month = FormatoUnicoExtractor.MONTH_MAP.get(month_name, 1)
            try:
                return date(year, month, day)
            except ValueError:
                pass

        return None

    @classmethod
    def clean_text_field(cls, value: str | None) -> str | None:
        """Clean string values, stripping delimiters and whitespace."""
        if not value:
            return None
        cleaned = re.sub(r"^[:\s\-\.]+|[:\s\-\.]+$", "", value.strip())
        return cleaned if cleaned else None

    @classmethod
    def get_field_value(
        cls,
        label_pattern: str,
        text: str,
        next_labels: list[str] | None = None,
    ) -> str | None:
        """
        Extract field value following label_pattern up to end of line or next label.
        """
        m = re.search(rf"{label_pattern}[:\s]*([^\n\r]+)", text, re.IGNORECASE)
        if not m:
            return None
        val = m.group(1)
        if next_labels:
            pattern = "|".join(re.escape(l) for l in next_labels)
            val = re.split(rf"(?:{pattern})", val, flags=re.IGNORECASE)[0]
        return cls.clean_text_field(val)

    def extract(
        self,
        full_text: str,
        page_texts: list[str] | None = None,
    ) -> CanonicalResume:
        """
        Extract canonical resume from full document text and page texts.
        """
        pages = page_texts if page_texts else [full_text]
        fields: list[ExtractedFieldItem] = []

        person = self._extract_person(full_text, pages, fields)
        contact = self._extract_contact(full_text, pages, fields)
        educations = self._extract_educations(full_text, pages, fields)
        languages = self._extract_languages(full_text, pages, fields)
        experiences = self._extract_work_experiences(full_text, pages, fields)
        summary = self._extract_experience_summary(full_text, pages, fields)

        return CanonicalResume(
            person=person,
            contact=contact,
            educations=educations,
            work_experiences=experiences,
            experience_summary=summary,
            languages=languages,
            extracted_fields=fields,
            metadata={"source_format": "FORMATO_UNICO_DAFP"},
        )

    # ------------------------------------------------------------
    # Section 1: Personal, Birth, Identification, Military
    # ------------------------------------------------------------
    def _extract_person(
        self,
        full_text: str,
        pages: list[str],
        fields: list[ExtractedFieldItem],
    ) -> CanonicalPerson:
        # Page 1 typically contains personal data
        text_p1 = pages[0] if pages else full_text

        # First & second surname
        first_surname = self.get_field_value(
            "PRIMER APELLIDO", text_p1, ["SEGUNDO APELLIDO", "NOMBRES", "DOCUMENTO"]
        )
        if first_surname:
            fields.append(ExtractedFieldItem(
                field_name="first_surname",
                raw_value=first_surname,
                normalized_value=first_surname,
                page_number=1,
            ))

        second_surname = self.get_field_value(
            "SEGUNDO APELLIDO", text_p1, ["NOMBRES", "DOCUMENTO"]
        )
        if second_surname:
            fields.append(ExtractedFieldItem(
                field_name="second_surname",
                raw_value=second_surname,
                normalized_value=second_surname,
                page_number=1,
            ))

        # Names
        first_name = None
        middle_name = None
        raw_names = self.get_field_value(
            "NOMBRES?", text_p1, ["DOCUMENTO", "IDENTIFICACI", "NACIONALIDAD", "SEXO"]
        )
        if raw_names:
            parts = raw_names.split()
            first_name = parts[0]
            if len(parts) > 1:
                middle_name = " ".join(parts[1:])
            fields.append(ExtractedFieldItem(
                field_name="first_name",
                raw_value=raw_names,
                normalized_value=first_name,
                page_number=1,
            ))


        # Identification
        id_type = "CC"
        id_number = None
        m = re.search(
            r"(?:DOCUMENTO DE IDENTIFICACI[OÓ]N|IDENTIFICACI[OÓ]N)[:\s]*(C\.?C\.?|C\.?E\.?|PASAPORTE|PEP|T\.?I\.?)?[:\s]*(?:N[Oº°\.]+|N[UÚ]MERO)?[:\s]*([0-9\.\,]+)",
            text_p1,
            re.IGNORECASE,
        )
        if m:
            if m.group(1):
                raw_type = m.group(1).upper().replace(".", "").strip()
                id_type = "CE" if "CE" in raw_type else "PASAPORTE" if "PAS" in raw_type else "CC"
            raw_id = m.group(2)
            id_number = re.sub(r"[^\d]", "", raw_id)
            fields.append(ExtractedFieldItem(
                field_name="identification_number",
                raw_value=raw_id,
                normalized_value=id_number,
                page_number=1,
            ))
        else:
            # Fallback for standalone number
            m_num = re.search(r"(?:C\.?C\.?|CEDULA)[:\s]*(?:N[Oº°\.]+|N[UÚ]MERO)?[:\s]*([0-9\.\,]{6,12})", text_p1, re.IGNORECASE)
            if m_num:
                id_number = re.sub(r"[^\d]", "", m_num.group(1))

        # Sex
        sex = None
        if re.search(r"\bSEXO[:\s]*(F|FEMENINO)\b", text_p1, re.IGNORECASE):
            sex = "FEMENINO"
        elif re.search(r"\bSEXO[:\s]*(M|MASCULINO)\b", text_p1, re.IGNORECASE):
            sex = "MASCULINO"

        # Nationality & Birth info
        nationality = "COLOMBIANA"
        m = re.search(r"NACIONALIDAD[:\s]+([A-Za-z]+)", text_p1, re.IGNORECASE)
        if m:
            nationality = self.clean_text_field(m.group(1)) or "COLOMBIANA"

        birth_date = None
        m = re.search(r"FECHA DE NACIMIENTO[:\s]*([0-9\/\-]+)", text_p1, re.IGNORECASE)
        if m:
            birth_date = self.parse_date(m.group(1))
        else:
            m_dmy = re.search(r"D[IÍ]A[:\s]*(\d{1,2})[\s]*MES[:\s]*(\d{1,2})[\s]*A[NÑ]O[:\s]*(\d{4})", text_p1, re.IGNORECASE)
            if m_dmy:
                try:
                    birth_date = date(int(m_dmy.group(3)), int(m_dmy.group(2)), int(m_dmy.group(1)))
                except ValueError:
                    pass

        birth_country = None
        m = re.search(r"PA[IÍ]S(?: DE NACIMIENTO)?[:\s]+([A-Za-z\s]+?)(?:DEPTO|DEPARTAMENTO|$)", text_p1, re.IGNORECASE)
        if m:
            birth_country = self.clean_text_field(m.group(1))

        birth_dept = None
        m = re.search(r"DEPARTAMENTO(?: DE NACIMIENTO)?[:\s]+([A-Za-z\s]+?)(?:MUNICIPIO|$)", text_p1, re.IGNORECASE)
        if m:
            birth_dept = self.clean_text_field(m.group(1))

        birth_mun = None
        m = re.search(r"MUNICIPIO(?: DE NACIMIENTO)?[:\s]+([A-Za-z\s]+?)(?:DIRECCI[OÓ]N|CORREO|TEL|$)", text_p1, re.IGNORECASE)
        if m:
            birth_mun = self.clean_text_field(m.group(1))

        # Military card
        mil_num = None
        mil_dist = None
        mil_class = None
        m = re.search(r"LIBRETA MILITAR[:\s]*(?:N[UÚ]MERO)?[:\s]*([0-9]+)", text_p1, re.IGNORECASE)
        if m:
            mil_num = m.group(1)
            fields.append(ExtractedFieldItem(
                field_name="military_card_number",
                raw_value=m.group(1),
                normalized_value=mil_num,
                page_number=1,
            ))

        m = re.search(r"DISTRITO[:\s]*([0-9A-Za-z]+)", text_p1, re.IGNORECASE)
        if m:
            mil_dist = self.clean_text_field(m.group(1))

        m = re.search(r"CLASE[:\s]*(PRIMERA|SEGUNDA|1|2)", text_p1, re.IGNORECASE)
        if m:
            raw_c = m.group(1).upper()
            mil_class = "PRIMERA" if raw_c in ("PRIMERA", "1") else "SEGUNDA"

        return CanonicalPerson(
            identification_type=id_type,
            identification_number=id_number,
            first_surname=first_surname,
            second_surname=second_surname,
            first_name=first_name,
            middle_name=middle_name,
            sex=sex,
            nationality=nationality,
            birth_date=birth_date,
            birth_country=birth_country,
            birth_department=birth_dept,
            birth_municipality=birth_mun,
            military_card_number=mil_num,
            military_card_district=mil_dist,
            military_card_class=mil_class,
        )

    # ------------------------------------------------------------
    # Section 1: Contact Information
    # ------------------------------------------------------------
    def _extract_contact(
        self,
        full_text: str,
        pages: list[str],
        fields: list[ExtractedFieldItem],
    ) -> CanonicalContact:
        text_p1 = pages[0] if pages else full_text

        # Email
        email = None
        m = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text_p1)
        if m:
            email = m.group(0).lower().strip()
            fields.append(ExtractedFieldItem(
                field_name="email",
                raw_value=m.group(0),
                normalized_value=email,
                page_number=1,
            ))

        # Telephone / Mobile
        phone = None
        m = re.search(r"(?:TEL[EÉ]FONO|TEL|CELULAR)[:\s]*([0-9\s\+\-\(\)]{7,25})", text_p1, re.IGNORECASE)
        if m:
            phone = self.clean_text_field(m.group(1))
            fields.append(ExtractedFieldItem(
                field_name="telephone",
                raw_value=m.group(1),
                normalized_value=phone,
                page_number=1,
            ))

        # Address
        address = self.get_field_value(
            "DIRECCI[OÓ]N", text_p1, ["PA[IÍ]S", "DEPTO", "DEPARTAMENTO", "MUNICIPIO", "TEL", "EMAIL", "CORREO"]
        )

        # Municipality / Department of residence
        mun = None
        dept = None
        country = "COLOMBIA"
        m = re.search(r"MUNICIPIO[:\s]+([A-Za-z\s]+?)(?:TEL|EMAIL|DIRECCI[OÓ]N|$)", text_p1, re.IGNORECASE)
        if m:
            mun = self.clean_text_field(m.group(1))

        return CanonicalContact(
            address=address,
            country=country,
            department=dept,
            municipality=mun,
            telephone=phone,
            mobile_phone=phone,
            email=email,
        )

    # ------------------------------------------------------------
    # Section 2: Academic Education
    # ------------------------------------------------------------
    def _extract_educations(
        self,
        full_text: str,
        pages: list[str],
        fields: list[ExtractedFieldItem],
    ) -> list[CanonicalEducation]:
        educations: list[CanonicalEducation] = []

        # High school / Básica y Media
        m_bach = re.search(
            r"(?:EDUCACI[OÓ]N B[AÁ]SICA Y MEDIA|BACHILLERATO)[:\s]*(?:T[IÍ]TULO OBTENIDO[:\s]*)?([^\n\r]+)",
            full_text,
            re.IGNORECASE,
        )
        if m_bach:
            raw_title = m_bach.group(1)
            # Remove any trailing inline markers if present
            cleaned_title = re.split(
                r"(?:FECHA DE GRADO|TERMINACI[OÓ]N|EDUCACI[OÓ]N SUPERIOR)",
                raw_title,
                flags=re.IGNORECASE,
            )[0]
            title = self.clean_text_field(cleaned_title)
            if title and len(title) > 3:
                educations.append(
                    CanonicalEducation(
                        level="HIGH_SCHOOL",
                        degree_title=title,
                        graduation_status="GRADUATED",
                        source_page=1,
                    )
                )

        # Higher Education (Pregrado / Postgrado / Universitaria)
        # Search patterns like: UNIVERSIDAD ... INGENIERO ...
        uni_patterns = [
            r"NOMBRE DE LA INSTITUCI[OÓ]N[:\s]*([^\n\r]+)",
            r"(?:UNIVERSIDAD|INSTITUCI[OÓ]N|COLEGIO MAYOR)[:\s]*([^\n\r]+)",
        ]

        # Extract higher education lines
        for page_idx, page_content in enumerate(pages):
            page_num = page_idx + 1
            if "FORMACION ACADEMICA" in page_content.upper() or "EDUCACION SUPERIOR" in page_content.upper() or "UNIVERSIDAD" in page_content.upper():
                # Focus on portion after EDUCACION SUPERIOR to avoid capturing high school title
                superior_text = page_content
                if re.search(r"EDUCACI[OÓ]N SUPERIOR", page_content, re.IGNORECASE):
                    superior_text = re.split(r"EDUCACI[OÓ]N SUPERIOR", page_content, flags=re.IGNORECASE)[-1]

                # Title
                m_title = re.search(
                    r"(?:T[IÍ]TULO O PROGRAMA ACAD[EÉ]MICO|T[IÍ]TULO O PROGRAMA|T[IÍ]TULO(?: OBTENIDO)?)[:\s]*([^\n\r]+)",
                    superior_text,
                    re.IGNORECASE,
                )
                degree = self.clean_text_field(m_title.group(1)) if m_title else None

                # Institution
                inst = None
                for p in uni_patterns:
                    m_inst = re.search(p, superior_text, re.IGNORECASE)
                    if m_inst:
                        inst = self.clean_text_field(m_inst.group(1))
                        if not inst.upper().startswith("UNIVERSIDAD") and "UNIVERSIDAD" in superior_text.upper():
                            m_uni = re.search(r"(UNIVERSIDAD [A-Za-z\s]+)", superior_text, re.IGNORECASE)
                            if m_uni:
                                inst = m_uni.group(1).strip()
                        break

                # Professional card
                card_no = None
                m_card = re.search(r"(?:TARJETA PROFESIONAL|T\.?P\.?)[:\s]*(?:N[UÚ]MERO)?[:\s]*([0-9A-Za-z]+)", superior_text, re.IGNORECASE)
                if m_card:
                    card_no = m_card.group(1)

                # Year of completion
                comp_year = None
                comp_month = None
                m_year = re.search(r"(?:A[NÑ]O|FECHA DE GRADO)[:\s]*(\d{4})", superior_text, re.IGNORECASE)
                if m_year:
                    comp_year = int(m_year.group(1))

                m_month = re.search(r"MES[:\s]*(\d{1,2})", superior_text, re.IGNORECASE)
                if m_month:
                    m_val = int(m_month.group(1))
                    if 1 <= m_val <= 12:
                        comp_month = m_val

                if degree or inst:
                    educations.append(
                        CanonicalEducation(
                            level="UNDERGRADUATE",
                            institution=inst,
                            degree_title=degree,
                            professional_card_no=card_no,
                            completion_year=comp_year,
                            completion_month=comp_month,
                            graduation_status="GRADUATED",
                            source_page=page_num,
                        )
                    )

        return educations

    # ------------------------------------------------------------
    # Section 2: Languages
    # ------------------------------------------------------------
    def _extract_languages(
        self,
        full_text: str,
        pages: list[str],
        fields: list[ExtractedFieldItem],
    ) -> list[CanonicalLanguage]:
        languages: list[CanonicalLanguage] = []
        # Common language mentions in DAFP form
        known_langs = ["INGLES", "INGLÉS", "FRANCES", "FRANCÉS", "ALEMAN", "ALEMÁN", "PORTUGUES", "PORTUGUÉS", "ITALIANO"]
        for lang in known_langs:
            if re.search(rf"\b{lang}\b", full_text, re.IGNORECASE):
                # Search proficiency (R, B, MB)
                norm_lang = "INGLES" if "INGL" in lang.upper() else "FRANCES" if "FRANC" in lang.upper() else lang.upper()
                # Default proficiency
                languages.append(
                    CanonicalLanguage(
                        language_name=norm_lang,
                        speaking="BIEN",
                        reading="BIEN",
                        writing="BIEN",
                        source_page=2 if len(pages) > 1 else 1,
                    )
                )
                break  # Avoid duplicates for accents

        return languages

    # ------------------------------------------------------------
    # Section 3: Work Experience
    # ------------------------------------------------------------
    def _extract_work_experiences(
        self,
        full_text: str,
        pages: list[str],
        fields: list[ExtractedFieldItem],
    ) -> list[CanonicalWorkExperience]:
        experiences: list[CanonicalWorkExperience] = []

        # Split text into experience blocks by "EMPRESA O ENTIDAD"
        exp_blocks = re.split(r"(?:EMPRESA O ENTIDAD|EMPLEO ACTUAL O CONTRATO)[:\s]*", full_text, flags=re.IGNORECASE)

        if len(exp_blocks) > 1:
            for idx, block in enumerate(exp_blocks[1:], start=1):
                # Company
                first_line = block.strip().split("\n")[0]
                company = self.clean_text_field(first_line)

                # Sector
                sector = "PUBLIC" if re.search(r"\bP[UÚ]BLICA\b", block, re.IGNORECASE) else "PRIVATE"

                # Position
                position = None
                m_pos = re.search(r"CARGO O CONTRATO(?: ACTUAL)?[:\s]*([^\n\r]+)", block, re.IGNORECASE)
                if m_pos:
                    position = self.clean_text_field(m_pos.group(1))

                # Dependency
                dept_unit = None
                m_dep = re.search(r"DEPENDENCIA[:\s]*([^\n\r]+)", block, re.IGNORECASE)
                if m_dep:
                    dept_unit = self.clean_text_field(m_dep.group(1))

                # Dates
                start_date = None
                m_start = re.search(r"FECHA DE INGRESO[:\s]*([0-9\/\-]+)", block, re.IGNORECASE)
                if m_start:
                    start_date = self.parse_date(m_start.group(1))

                end_date = None
                m_end = re.search(r"FECHA DE RETIRO[:\s]*([0-9\/\-]+)", block, re.IGNORECASE)
                if m_end:
                    end_date = self.parse_date(m_end.group(1))

                if company and len(company) > 2:
                    experiences.append(
                        CanonicalWorkExperience(
                            company_name=company,
                            sector=sector,
                            position=position,
                            department_unit=dept_unit,
                            start_date=start_date,
                            end_date=end_date,
                            is_current=(end_date is None),
                            source_page=min(idx + 1, len(pages)),
                        )
                    )

        return experiences

    # ------------------------------------------------------------
    # Section 4: Total Experience Summary
    # ------------------------------------------------------------
    def _extract_experience_summary(
        self,
        full_text: str,
        pages: list[str],
        fields: list[ExtractedFieldItem],
    ) -> CanonicalExperienceSummary | None:
        if "TIEMPO TOTAL DE EXPERIENCIA" not in full_text.upper() and "TIEMPO DE EXPERIENCIA" not in full_text.upper():
            return None

        # Search for years and months patterns
        pub_y, pub_m = 0, 0
        priv_y, priv_m = 0, 0
        ind_y, ind_m = 0, 0
        tot_y, tot_m = 0, 0

        # General pattern: TIEMPO TOTAL DE EXPERIENCIA: (\d+) AÑOS, (\d+) MESES
        m_tot = re.search(r"TIEMPO TOTAL DE EXPERIENCIA[:\s]*(\d+)[\s]*A[NÑ]OS?(?:[,\s]*(\d+)[\s]*MESES?)?", full_text, re.IGNORECASE)
        if m_tot:
            tot_y = int(m_tot.group(1))
            tot_m = int(m_tot.group(2)) if m_tot.group(2) else 0

        m_pub = re.search(r"SERVIDOR P[UÚ]BLICO[:\s]*(\d+)[\s]*A[NÑ]OS?(?:[,\s]*(\d+)[\s]*MESES?)?", full_text, re.IGNORECASE)
        if m_pub:
            pub_y = int(m_pub.group(1))
            pub_m = int(m_pub.group(2)) if m_pub.group(2) else 0

        m_priv = re.search(r"SECTOR PRIVADO[:\s]*(\d+)[\s]*A[NÑ]OS?(?:[,\s]*(\d+)[\s]*MESES?)?", full_text, re.IGNORECASE)
        if m_priv:
            priv_y = int(m_priv.group(1))
            priv_m = int(m_priv.group(2)) if m_priv.group(2) else 0

        return CanonicalExperienceSummary(
            public_years=pub_y,
            public_months=pub_m,
            private_years=priv_y,
            private_months=priv_m,
            independent_years=ind_y,
            independent_months=ind_m,
            total_years=tot_y,
            total_months=tot_m,
        )
