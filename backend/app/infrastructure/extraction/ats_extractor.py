"""
ATS Resume Extractor: Structured data extraction for free-form / open resumes
in Spanish and English.
"""

from datetime import date
import re
from typing import Any
import structlog

from app.domain.entities.canonical_resume import (
    CanonicalContact,
    CanonicalEducation,
    CanonicalLanguage,
    CanonicalPerson,
    CanonicalResume,
    CanonicalWorkExperience,
    ExtractedFieldItem,
)

logger = structlog.get_logger(__name__)

# Common skills taxonomy for ATS parsing
COMMON_SKILLS: list[str] = [
    # Languages
    "Python", "JavaScript", "TypeScript", "Java", "C++", "C#", "Go", "Rust",
    "PHP", "Ruby", "Kotlin", "Swift", "SQL", "HTML", "CSS", "Bash", "R",
    # Frontend & Backend Frameworks
    "React", "Angular", "Vue", "Next.js", "Node.js", "Express", "FastAPI",
    "Django", "Flask", "Spring Boot", "Spring", "ASP.NET", ".NET", "Laravel",
    # Data & AI
    "PyTorch", "TensorFlow", "Pandas", "NumPy", "Scikit-learn", "Keras",
    "Data Science", "Machine Learning", "Deep Learning", "Power BI", "Tableau",
    # Databases
    "PostgreSQL", "MySQL", "MongoDB", "Redis", "SQLite", "Oracle",
    "Microsoft SQL Server", "Elasticsearch", "DynamoDB", "Cassandra",
    # Cloud & DevOps
    "AWS", "Azure", "GCP", "Google Cloud", "Docker", "Kubernetes", "Terraform",
    "Ansible", "CI/CD", "GitHub Actions", "GitLab CI", "Jenkins", "Linux",
    "Git", "Microservices", "REST API", "GraphQL",
    # Management & Methodologies
    "Agile", "Scrum", "Kanban", "Jira", "DevOps",
]

SPANISH_MONTHS: dict[str, int] = {
    "enero": 1, "ene": 1, "febrero": 2, "feb": 2, "marzo": 3, "mar": 3,
    "abril": 4, "abr": 4, "mayo": 5, "may": 5, "junio": 6, "jun": 6,
    "julio": 7, "jul": 7, "agosto": 8, "ago": 8, "septiembre": 9, "sep": 9, "set": 9,
    "octubre": 10, "oct": 10, "noviembre": 11, "nov": 11, "diciembre": 12, "dic": 12,
}

ENGLISH_MONTHS: dict[str, int] = {
    "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3,
    "april": 4, "apr": 4, "may": 5, "june": 6, "jun": 6,
    "july": 7, "jul": 7, "august": 8, "aug": 8, "september": 9, "sep": 9,
    "october": 10, "oct": 10, "november": 11, "nov": 11, "december": 12, "dec": 12,
}


class AtsResumeExtractor:
    """
    Heuristic, rule-based semantic extractor for free-form resumes (ATS format)
    in Spanish and English.
    """

    def __init__(self) -> None:
        self._skills_set = {s.upper(): s for s in COMMON_SKILLS}

    def extract(
        self,
        full_text: str,
        page_texts: list[str] | None = None,
    ) -> CanonicalResume:
        """
        Extract structured canonical resume from free-form resume text.
        """
        if not full_text or not full_text.strip():
            return CanonicalResume(metadata={"source_format": "ATS"})

        pages = page_texts or [full_text]
        fields: list[ExtractedFieldItem] = []

        # 1. Segment text into semantic sections
        sections = self._segment_sections(full_text)

        # 2. Extract Header & Contact
        person, contact = self._extract_header_and_contact(
            sections.get("header", ""), full_text, fields
        )

        # 3. Extract Summary
        summary = self._extract_summary(sections.get("summary", ""))

        # 4. Extract Work Experience
        work_experiences = self._extract_work_experience(
            sections.get("experience", ""), fields
        )

        # 5. Extract Education
        educations = self._extract_education(
            sections.get("education", ""), fields
        )

        # 6. Extract Skills
        skills = self._extract_skills(sections.get("skills", ""), full_text)

        # 7. Extract Languages
        languages = self._extract_languages(sections.get("languages", ""), full_text)

        # 8. Extract Certifications
        certifications = self._extract_certifications(
            sections.get("certifications", "")
        )

        # 9. Extract Professional URLs
        urls = self._extract_urls(full_text)

        metadata: dict[str, Any] = {
            "source_format": "ATS",
            "skills": skills,
            "certifications": certifications,
            "professional_urls": urls,
        }
        if summary:
            metadata["summary"] = summary

        return CanonicalResume(
            person=person,
            contact=contact,
            educations=educations,
            work_experiences=work_experiences,
            languages=languages,
            extracted_fields=fields,
            metadata=metadata,
        )

    # ------------------------------------------------------------
    # Section Segmentation
    # ------------------------------------------------------------
    def _segment_sections(self, text: str) -> dict[str, str]:
        """
        Identifies section headers in Spanish and English and divides text.
        """
        section_patterns = [
            (
                "summary",
                r"(?:^|\n)\s*(?:RESUMEN\s+PROFESIONAL|PERFIL\s+PROFESIONAL|PERFIL|SOBRE\s+M[IÍ]|ACERCA\s+DE\s+M[IÍ]|EXTRACTO|PROFESSIONAL\s+SUMMARY|SUMMARY|PROFILE|ABOUT\s+ME|EXECUTIVE\s+SUMMARY|OBJECTIVE)[:\s]*\n?",
            ),
            (
                "experience",
                r"(?:^|\n)\s*(?:EXPERIENCIA\s+LABORAL|EXPERIENCIA\s+PROFESIONAL|EXPERIENCIA\s+DE\s+TRABAJO|EXPERIENCIA|TRAYECTORIA\s+LABORAL|HISTORIAL\s+LABORAL|WORK\s+EXPERIENCE|PROFESSIONAL\s+EXPERIENCE|EXPERIENCE|EMPLOYMENT\s+HISTORY|WORK\s+HISTORY)[:\s]*\n?",
            ),
            (
                "education",
                r"(?:^|\n)\s*(?:EDUCACI[OÓ]N\s+Y\s+FORMACI[OÓ]N|EDUCACI[OÓ]N|FORMACI[OÓ]N\s+ACAD[EÉ]MICA|ESTUDIOS|FORMACI[OÓ]N|EDUCATION|ACADEMIC\s+BACKGROUND|ACADEMIC\s+HISTORY|STUDIES)[:\s]*\n?",
            ),
            (
                "skills",
                r"(?:^|\n)\s*(?:HABILIDADES\s+T[EÉ]CNICAS|HABILIDADES|COMPETENCIAS|CONOCIMIENTOS|TECNOLOG[IÍ]AS|STACK\s+TECNOL[OÓ]GICO|APTITUDES|SKILLS|TECHNICAL\s+SKILLS|CORE\s+COMPETENCIES|TECHNOLOGIES|TECH\s+STACK|AREAS\s+OF\s+EXPERTISE)[:\s]*\n?",
            ),
            (
                "languages",
                r"(?:^|\n)\s*(?:IDIOMAS|LENGUAS|LANGUAGES|LANGUAGE\s+PROFICIENCY)[:\s]*\n?",
            ),
            (
                "certifications",
                r"(?:^|\n)\s*(?:CERTIFICACIONES|CERTIFICADOS|CURSOS\s+Y\s+CERTIFICACIONES|LICENCIAS\s+Y\s+CERTIFICACIONES|CERTIFICATIONS|CERTIFICATES|LICENSES\s+&\s+CERTIFICATIONS|COURSES\s+&\s+CERTIFICATIONS)[:\s]*\n?",
            ),
            (
                "projects",
                r"(?:^|\n)\s*(?:PROYECTOS|PORTAFOLIO|PROJECTS|PORTFOLIO)[:\s]*\n?",
            ),
        ]

        # Find match indices
        matches: list[tuple[int, int, str]] = []
        for sec_name, pattern in section_patterns:
            for m in re.finditer(pattern, text, re.IGNORECASE):
                matches.append((m.start(), m.end(), sec_name))

        matches.sort(key=lambda x: x[0])

        sections: dict[str, str] = {}
        if not matches:
            sections["header"] = text
            return sections

        # Content before the first matched header is the header / contact block
        first_start, _, _ = matches[0]
        sections["header"] = text[:first_start].strip()

        for idx, (m_start, m_end, sec_name) in enumerate(matches):
            next_start = matches[idx + 1][0] if idx + 1 < len(matches) else len(text)
            content = text[m_end:next_start].strip()
            # If section repeated, append
            if sec_name in sections:
                sections[sec_name] += "\n\n" + content
            else:
                sections[sec_name] = content

        return sections

    # ------------------------------------------------------------
    # Header & Contact Extraction
    # ------------------------------------------------------------
    def _extract_header_and_contact(
        self,
        header_text: str,
        full_text: str,
        fields: list[ExtractedFieldItem],
    ) -> tuple[CanonicalPerson, CanonicalContact]:
        target_text = header_text if header_text else full_text

        # 1. Full name
        first_name = None
        middle_name = None
        first_surname = None
        second_surname = None
        full_name = None

        lines = [line.strip() for line in target_text.splitlines() if line.strip()]
        for line in lines[:6]:
            # Discard obvious non-name lines
            upper = line.upper()
            if any(skip in upper for skip in ["CURRICULUM", "HOJA DE VIDA", "RESUME", "@", "HTTP", "WWW", "TEL", "+"]):
                continue
            if re.search(r"\d", line):
                continue
            # Candidate line: 2 to 5 words, letters only
            words = line.split()
            if 2 <= len(words) <= 5 and all(w.replace(".", "").isalpha() for w in words):
                full_name = line.strip()
                if len(words) == 2:
                    first_name = words[0]
                    first_surname = words[1]
                elif len(words) == 3:
                    first_name = words[0]
                    first_surname = words[1]
                    second_surname = words[2]
                elif len(words) == 4:
                    first_name = words[0]
                    middle_name = words[1]
                    first_surname = words[2]
                    second_surname = words[3]
                else:
                    first_name = words[0]
                    first_surname = words[-1]
                break

        if full_name:
            fields.append(
                ExtractedFieldItem(
                    field_name="full_name",
                    raw_value=full_name,
                    normalized_value=full_name,
                    page_number=1,
                    confidence=0.90,
                )
            )

        # 2. Identification number (if present)
        id_type = None
        id_num = None
        m_id = re.search(
            r"(?:C\.?C\.?|C[EÉ]|DNI|PASAPORTE|CEDULA|IDENTIFICACI[OÓ]N|ID)[:\s#]*([0-9\.\-]+)",
            full_text,
            re.IGNORECASE,
        )
        if m_id:
            raw_id = m_id.group(1).strip()
            clean_id = re.sub(r"[^\d]", "", raw_id)
            if len(clean_id) >= 6:
                id_type = "CC"
                id_num = clean_id
                fields.append(
                    ExtractedFieldItem(
                        field_name="identification_number",
                        raw_value=raw_id,
                        normalized_value=clean_id,
                        page_number=1,
                    )
                )

        # 3. Email
        email = None
        m_email = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", full_text)
        if m_email:
            email = m_email.group(0).lower().strip()
            fields.append(
                ExtractedFieldItem(
                    field_name="email",
                    raw_value=m_email.group(0),
                    normalized_value=email,
                    page_number=1,
                )
            )

        # 4. Telephone / Mobile
        phone = None
        m_phone = re.search(
            r"(?:\+?\d{1,3}[\s-]?)?(?:\(?\d{2,4}\)?[\s.-]?)?\d{3,4}[\s.-]?\d{3,4}",
            target_text,
        )
        if m_phone:
            raw_ph = m_phone.group(0).strip()
            if len(re.sub(r"[^\d]", "", raw_ph)) >= 7:
                phone = raw_ph
                fields.append(
                    ExtractedFieldItem(
                        field_name="telephone",
                        raw_value=raw_ph,
                        normalized_value=phone,
                        page_number=1,
                    )
                )

        # 5. Location (City, Country / Department)
        city = None
        country = None
        m_loc = re.search(
            r"(?:UBICACI[OÓ]N|LOCATION|DIRECCI[OÓ]N|ADDRESS)?[:\s]*([A-ZÁÉÍÓÚ][a-záéíóú]+(?:\s+[A-ZÁÉÍÓÚ][a-záéíóú]+)?),\s*([A-ZÁÉÍÓÚ][a-záéíóú]+(?:\s+[A-ZÁÉÍÓÚ][a-záéíóú]+)?)",
            target_text,
        )
        if m_loc:
            city = m_loc.group(1).strip()
            country = m_loc.group(2).strip()

        person = CanonicalPerson(
            identification_type=id_type,
            identification_number=id_num,
            first_surname=first_surname,
            second_surname=second_surname,
            first_name=first_name,
            middle_name=middle_name,
        )

        contact = CanonicalContact(
            address=None,
            country=country,
            municipality=city,
            telephone=phone,
            mobile_phone=phone,
            email=email,
        )

        return person, contact

    # ------------------------------------------------------------
    # Summary Extraction
    # ------------------------------------------------------------
    def _extract_summary(self, summary_text: str) -> str | None:
        if not summary_text:
            return None
        cleaned = " ".join(summary_text.split())
        return cleaned if len(cleaned) > 20 else None

    # ------------------------------------------------------------
    # Work Experience Extraction
    # ------------------------------------------------------------
    def _extract_work_experience(
        self,
        exp_text: str,
        fields: list[ExtractedFieldItem],
    ) -> list[CanonicalWorkExperience]:
        if not exp_text or not exp_text.strip():
            return []

        experiences: list[CanonicalWorkExperience] = []

        # Date range pattern matching:
        # e.g., "Ene 2020 - Dic 2022", "March 2019 - Present", "2018 - 2021", "01/2019 - 12/2021"
        date_range_pattern = re.compile(
            r"(?P<start>(?:[A-Za-z]{3,10}\.?\s+)?(?:\d{1,2}[/-])?\d{4})"
            r"\s*(?:-|–|—|al?|to)\s*"
            r"(?P<end>(?:[A-Za-z]{3,10}\.?\s+)?(?:\d{1,2}[/-])?\d{4}|Presente|Actualidad|Present|Current)",
            re.IGNORECASE,
        )

        lines = [l.strip() for l in exp_text.splitlines() if l.strip()]
        if not lines:
            return []

        # Find all lines containing a date range
        date_indices: list[tuple[int, re.Match]] = []
        for idx, line in enumerate(lines):
            m = date_range_pattern.search(line)
            if m:
                date_indices.append((idx, m))

        if not date_indices:
            return []

        role_indicators = [
            "ENGINEER", "INGENIER", "DEVELOPER", "DESARROLLADOR", "ARCHITECT", "ARQUITECT",
            "LEAD", "LIDER", "LÍDER", "MANAGER", "GERENTE", "DIRECTOR", "ANALYST", "ANALISTA",
            "CONSULTANT", "CONSULTOR", "SPECIALIST", "ESPECIALISTA", "ADMINISTRATOR", "ADMINISTRADOR",
            "COORDINATOR", "COORDINADOR", "ASESOR", "AUXILIAR", "TECNICO", "TÉCNICO", "PRACTICANTE",
            "INTERN", "DESIGNER", "DISEÑADOR", "SCIENTIST", "CIENTIFICO", "CIENTÍFICO", "TECH",
        ]

        def is_role(candidate: str) -> bool:
            u = candidate.upper()
            return any(ind in u for ind in role_indicators)

        for i, (date_line_idx, m_date) in enumerate(date_indices):
            prev_date_idx = date_indices[i - 1][0] if i > 0 else -1
            next_date_idx = date_indices[i + 1][0] if i + 1 < len(date_indices) else len(lines)

            # Header lines are the non-bullet lines immediately preceding this date line
            candidate_headers = lines[prev_date_idx + 1 : date_line_idx]
            header_lines: list[str] = []
            for h_line in reversed(candidate_headers):
                if h_line.startswith(("-", "•", "*", "–")):
                    break
                header_lines.insert(0, h_line)
                if len(header_lines) >= 2:
                    break

            if not header_lines and candidate_headers:
                header_lines = [candidate_headers[-1]]

            # Also check if title or company was inline on the date line
            inline_text = lines[date_line_idx][: m_date.start()].strip()
            if inline_text:
                header_lines.append(inline_text)

            start_str = m_date.group("start").strip()
            end_str = m_date.group("end").strip()

            start_date = self._parse_flexible_date(start_str)
            is_current = any(
                curr in end_str.upper() for curr in ["PRESENTE", "ACTUALIDAD", "PRESENT", "CURRENT"]
            )
            end_date = None if is_current else self._parse_flexible_date(end_str)

            # Look for Company and Position in header_lines
            company = None
            position = None

            if len(header_lines) >= 2:
                h0, h1 = header_lines[0], header_lines[1]
                if is_role(h0) and not is_role(h1):
                    position, company = h0, h1
                elif is_role(h1) and not is_role(h0):
                    position, company = h1, h0
                else:
                    position, company = h0, h1
            elif len(header_lines) == 1:
                hl = header_lines[0]
                if " - " in hl:
                    parts = hl.split(" - ", 1)
                    p0, p1 = parts[0].strip(), parts[1].strip()
                    if is_role(p0) and not is_role(p1):
                        position, company = p0, p1
                    elif is_role(p1) and not is_role(p0):
                        position, company = p1, p0
                    else:
                        company, position = p0, p1
                elif " | " in hl:
                    parts = hl.split(" | ", 1)
                    p0, p1 = parts[0].strip(), parts[1].strip()
                    if is_role(p0) and not is_role(p1):
                        position, company = p0, p1
                    elif is_role(p1) and not is_role(p0):
                        position, company = p1, p0
                    else:
                        company, position = p0, p1
                elif " at " in hl.lower():
                    parts = re.split(r"\s+at\s+", hl, flags=re.IGNORECASE)
                    position, company = parts[0].strip(), parts[1].strip()
                elif " en " in hl.lower():
                    parts = re.split(r"\s+en\s+", hl, flags=re.IGNORECASE)
                    position, company = parts[0].strip(), parts[1].strip()
                else:
                    position = hl
                    company = "Confidencial"
            else:
                position = "Profesional"
                company = "Empresa"

            # Clean any trailing separators
            company = re.sub(r"^[|\-–—:]\s*", "", company).strip()
            position = re.sub(r"^[|\-–—:]\s*", "", position).strip()

            # Description lines are lines between current date line and the next job's header
            if i + 1 < len(date_indices):
                between_lines = lines[date_line_idx + 1 : next_date_idx]
                next_header_count = 0
                for cand in reversed(between_lines):
                    if cand.startswith(("-", "•", "*", "–")):
                        break
                    next_header_count += 1
                    if next_header_count >= 2:
                        break
                if next_header_count == 0 and between_lines:
                    next_header_count = 1
                desc_lines = between_lines[: len(between_lines) - next_header_count]
            else:
                desc_lines = lines[date_line_idx + 1 :]

            responsibilities = "\n".join(desc_lines).strip() if desc_lines else None

            # Detect sector
            sector = "PUBLIC" if any(
                p in company.upper() for p in ["MINISTERIO", "ALCALD", "GOBERNACI", "SECRETAR", "DIAN", "HOSPITAL"]
            ) else "PRIVATE"

            if company:
                fields.append(
                    ExtractedFieldItem(
                        field_name="company_name",
                        raw_value=company,
                        normalized_value=company,
                        page_number=1,
                    )
                )

            experiences.append(
                CanonicalWorkExperience(
                    company_name=company,
                    position=position,
                    sector=sector,
                    start_date=start_date,
                    end_date=end_date,
                    is_current=is_current,
                    responsibilities=responsibilities,
                    source_page=1,
                )
            )

        return experiences

    # ------------------------------------------------------------
    # Education Extraction
    # ------------------------------------------------------------
    def _extract_education(
        self,
        edu_text: str,
        fields: list[ExtractedFieldItem],
    ) -> list[CanonicalEducation]:
        if not edu_text or not edu_text.strip():
            return []

        educations: list[CanonicalEducation] = []
        blocks = edu_text.split("\n\n")

        for block in blocks:
            lines = [l.strip() for l in block.splitlines() if l.strip()]
            if not lines:
                continue

            full_block = " ".join(lines)

            # 1. Infer Level
            level = "UNDERGRADUATE"
            upper_block = full_block.upper()
            if any(term in upper_block for term in ["DOCTOR", "PHD", "PH.D."]):
                level = "DOCTORATE"
            elif any(term in upper_block for term in ["MÁSTER", "MASTER", "MAGISTER", "MAESTRÍA", "MSC", "M.S."]):
                level = "MASTER"
            elif any(term in upper_block for term in ["ESPECIALIZACI", "POSTGRADO", "DIPLOMADO"]):
                level = "POSTGRADUATE"
            elif any(term in upper_block for term in ["TECNÓLOG", "TECNOLOG", "TECHNOLOGY"]):
                level = "TECHNOLOGY"
            elif any(term in upper_block for term in ["TÉCNIC", "TECNIC"]):
                level = "TECHNICAL"
            elif any(term in upper_block for term in ["BACHILLER", "HIGH SCHOOL"]):
                level = "HIGH_SCHOOL"

            # 2. Extract Year
            comp_year = None
            m_year = re.search(r"\b(19\d{2}|20\d{2})\b", full_block)
            if m_year:
                comp_year = int(m_year.group(1))

            # 3. Degree title & Institution
            degree_title = None
            institution = None

            if len(lines) >= 2:
                degree_title = lines[0]
                institution = lines[1]
            elif len(lines) == 1:
                line = lines[0]
                if " - " in line:
                    parts = line.split(" - ", 1)
                    degree_title, institution = parts[0].strip(), parts[1].strip()
                elif " | " in line:
                    parts = line.split(" | ", 1)
                    degree_title, institution = parts[0].strip(), parts[1].strip()
                else:
                    degree_title = line

            # Clean years from title or institution
            if degree_title:
                degree_title = re.sub(r"\b(19\d{2}|20\d{2})\b", "", degree_title).strip()
            if institution:
                institution = re.sub(r"\b(19\d{2}|20\d{2})\b", "", institution).strip()

            if degree_title:
                fields.append(
                    ExtractedFieldItem(
                        field_name="degree_title",
                        raw_value=degree_title,
                        normalized_value=degree_title,
                        page_number=1,
                    )
                )

            educations.append(
                CanonicalEducation(
                    level=level,
                    institution=institution,
                    degree_title=degree_title,
                    completion_year=comp_year,
                    graduation_status="GRADUATED",
                    source_page=1,
                )
            )

        return educations

    # ------------------------------------------------------------
    # Skills Extraction
    # ------------------------------------------------------------
    def _extract_skills(self, skills_text: str, full_text: str) -> list[str]:
        target = skills_text if skills_text else full_text
        found_skills: set[str] = set()

        for skill_upper, skill_canonical in self._skills_set.items():
            # Use regex with word boundary
            pattern = r"\b" + re.escape(skill_upper) + r"\b"
            if re.search(pattern, target.upper()):
                found_skills.add(skill_canonical)

        return sorted(found_skills)

    # ------------------------------------------------------------
    # Languages Extraction
    # ------------------------------------------------------------
    def _extract_languages(
        self, languages_text: str, full_text: str
    ) -> list[CanonicalLanguage]:
        target = languages_text if languages_text else full_text
        languages: list[CanonicalLanguage] = []

        lang_keywords = [
            ("INGLES", ["INGLÉS", "INGLES", "ENGLISH"]),
            ("ESPAÑOL", ["ESPAÑOL", "SPANISH", "CASTELLANO"]),
            ("FRANCES", ["FRANCÉS", "FRANCES", "FRENCH"]),
            ("ALEMAN", ["ALEMÁN", "ALEMAN", "GERMAN"]),
            ("PORTUGUES", ["PORTUGUÉS", "PORTUGUES", "PORTUGUESE"]),
            ("ITALIANO", ["ITALIANO", "ITALIAN"]),
        ]

        for lang_name, variants in lang_keywords:
            for v in variants:
                pattern = r"\b" + re.escape(v) + r"\b"
                m = re.search(pattern, target, re.IGNORECASE)
                if m:
                    # Look for proficiency on same line or surrounding context
                    line = target[max(0, m.start() - 20) : min(len(target), m.end() + 40)].upper()
                    proficiency = "BIEN"
                    if any(term in line for term in ["NATIVO", "NATIVE", "C1", "C2", "AVANZADO", "ADVANCED", "FLUENT"]):
                        proficiency = "MUY_BIEN"
                    elif any(term in line for term in ["BÁSICO", "BASICO", "BASIC", "A1", "A2", "ELEMENTARY"]):
                        proficiency = "REGULAR"

                    languages.append(
                        CanonicalLanguage(
                            language_name=lang_name,
                            speaking=proficiency,
                            reading=proficiency,
                            writing=proficiency,
                            source_page=1,
                        )
                    )
                    break

        return languages

    # ------------------------------------------------------------
    # Certifications Extraction
    # ------------------------------------------------------------
    def _extract_certifications(self, cert_text: str) -> list[dict[str, Any]]:
        if not cert_text:
            return []

        certifications: list[dict[str, Any]] = []
        lines = [l.strip() for l in cert_text.splitlines() if l.strip()]
        for line in lines:
            if len(line) < 5:
                continue
            # Extract year if present
            m_year = re.search(r"\b(19\d{2}|20\d{2})\b", line)
            year = int(m_year.group(1)) if m_year else None
            clean_name = re.sub(r"\b(19\d{2}|20\d{2})\b", "", line).strip(" -|:,")

            certifications.append({
                "name": clean_name,
                "year": year,
            })

        return certifications

    # ------------------------------------------------------------
    # Professional URLs Extraction
    # ------------------------------------------------------------
    def _extract_urls(self, text: str) -> list[str]:
        patterns = [
            r"https?://(?:www\.)?linkedin\.com/in/[a-zA-Z0-9_\-]+/?",
            r"https?://(?:www\.)?github\.com/[a-zA-Z0-9_\-]+/?",
            r"https?://(?:www\.)?gitlab\.com/[a-zA-Z0-9_\-]+/?",
            r"https?://(?:www\.)?behance\.net/[a-zA-Z0-9_\-]+/?",
            r"linkedin\.com/in/[a-zA-Z0-9_\-]+/?",
            r"github\.com/[a-zA-Z0-9_\-]+/?",
        ]
        urls: set[str] = set()
        for p in patterns:
            for match in re.finditer(p, text, re.IGNORECASE):
                urls.add(match.group(0).strip())

        return sorted(urls)

    # ------------------------------------------------------------
    # Date parsing helper
    # ------------------------------------------------------------
    def _parse_flexible_date(self, text: str) -> date | None:
        """
        Parses dates like 'Ene 2020', 'March 2019', '01/2020', '2018'.
        """
        if not text:
            return None

        clean = text.strip()

        # Format: DD/MM/YYYY or MM/YYYY
        m = re.match(r"^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$", clean)
        if m:
            d, mth, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
            try:
                return date(y, mth, d)
            except ValueError:
                pass

        m = re.match(r"^(\d{1,2})[/-](\d{4})$", clean)
        if m:
            mth, y = int(m.group(1)), int(m.group(2))
            if 1 <= mth <= 12:
                return date(y, mth, 1)

        # Format: "Ene 2020", "March 2019"
        words = clean.split()
        if len(words) == 2:
            mth_str, y_str = words[0].lower().rstrip("."), words[1]
            if y_str.isdigit() and len(y_str) == 4:
                year = int(y_str)
                month = SPANISH_MONTHS.get(mth_str) or ENGLISH_MONTHS.get(mth_str)
                if month:
                    return date(year, month, 1)

        # Year only: "2018"
        m = re.match(r"^(\d{4})$", clean)
        if m:
            return date(int(m.group(1)), 1, 1)

        return None
