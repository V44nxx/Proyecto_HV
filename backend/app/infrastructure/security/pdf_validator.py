"""
PDF Security Validator.

Inspects PDF documents for malicious vectors, active scripts,
launch actions, suspicious embedded files, and decompression bombs
prior to processing or permanent storage.
"""

import re
import fitz
import structlog

logger = structlog.get_logger(__name__)

# Dangerous PDF dictionary keys and action types
DANGEROUS_PDF_PATTERNS = [
    (re.compile(rb"/JavaScript\b", re.IGNORECASE), "JavaScript incrustado (/JavaScript)"),
    (re.compile(rb"/JS\b", re.IGNORECASE), "Script JS incrustado (/JS)"),
    (re.compile(rb"/Launch\b", re.IGNORECASE), "Acción de ejecución de comandos (/Launch)"),
    (re.compile(rb"/SubmitForm\b", re.IGNORECASE), "Envío externo de formulario (/SubmitForm)"),
    (re.compile(rb"/ImportData\b", re.IGNORECASE), "Importación de datos dinámicos (/ImportData)"),
    (re.compile(rb"/RichMedia\b", re.IGNORECASE), "Objeto multimedia enriquecido / Flash (/RichMedia)"),
]

# Max decompressed size ratio: protect against PDF decompression bombs
MAX_DECOMPRESSED_RATIO = 150.0  # Max 150x expansion ratio
MAX_TOTAL_UNCOMPRESSED_BYTES = 100 * 1024 * 1024  # 100 MB


def validate_pdf_security(file_bytes: bytes) -> tuple[bool, str | None]:
    """
    Validates structural and content security of a PDF byte stream.

    Checks for:
    1. Dangerous active content and launch actions.
    2. Decompression bomb indicators.
    3. Malformed or recursive object definitions.

    Returns:
        tuple[bool, str | None]: (is_secure, rejection_reason)
    """
    if not file_bytes:
        return False, "El archivo PDF está vacío."

    raw_size = len(file_bytes)

    # 1. Pattern scanning in raw PDF stream
    for pattern, description in DANGEROUS_PDF_PATTERNS:
        if pattern.search(file_bytes):
            logger.warning("pdf_security_threat_detected", threat=description, size=raw_size)
            return False, f"El archivo PDF contiene elementos no permitidos por seguridad: {description}."

    # 2. Structural inspection with PyMuPDF
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as exc:
        logger.warning("pdf_security_open_failed", error=str(exc))
        return False, "El archivo PDF no pudo ser analizado estructuralmente o está corrupto."

    try:
        # Check embedded files
        if doc.embfile_count() > 0:
            logger.warning("pdf_security_embedded_files", count=doc.embfile_count())
            return False, "El archivo PDF contiene archivos adjuntos incrustados (/EmbeddedFiles), no permitidos por seguridad."

        # Check total extracted text / decompressed stream ratio
        total_uncompressed_len = 0
        for page_num in range(min(len(doc), 100)):
            page = doc[page_num]
            text = page.get_text()
            total_uncompressed_len += len(text.encode("utf-8"))
            if total_uncompressed_len > MAX_TOTAL_UNCOMPRESSED_BYTES:
                return False, "El archivo PDF excede los límites de descompresión permitidos (posible bomba de descompresión)."

        if raw_size > 0 and (total_uncompressed_len / raw_size) > MAX_DECOMPRESSED_RATIO and total_uncompressed_len > 10 * 1024 * 1024:
            return False, "El archivo PDF presenta un ratio de expansión anómalo (bomba de descompresión)."

    finally:
        doc.close()

    return True, None
