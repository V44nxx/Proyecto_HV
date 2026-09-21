"""
Unit tests for the PDF security validator.
"""

import fitz
import pytest

from app.infrastructure.security.pdf_validator import validate_pdf_security


def _make_clean_pdf(text: str = "Documento institucional seguro.") -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), text)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def test_clean_pdf_passes_security():
    pdf_bytes = _make_clean_pdf()
    is_secure, reason = validate_pdf_security(pdf_bytes)
    assert is_secure is True
    assert reason is None


def test_empty_bytes_rejected():
    is_secure, reason = validate_pdf_security(b"")
    assert is_secure is False
    assert "vacío" in (reason or "").lower()


def test_pdf_with_javascript_rejected():
    clean_bytes = _make_clean_pdf()
    # Inject /JavaScript dictionary key
    malicious_bytes = clean_bytes + b"\n% /JavaScript << /JS (app.alert(1)) >>\n"
    is_secure, reason = validate_pdf_security(malicious_bytes)
    assert is_secure is False
    assert "JavaScript" in (reason or "")


def test_pdf_with_launch_action_rejected():
    clean_bytes = _make_clean_pdf()
    malicious_bytes = clean_bytes + b"\n% /Launch << /F (cmd.exe) >>\n"
    is_secure, reason = validate_pdf_security(malicious_bytes)
    assert is_secure is False
    assert "Launch" in (reason or "")


def test_pdf_with_embedded_files_rejected():
    doc = fitz.open()
    doc.new_page()
    # Embed a dummy file
    doc.embfile_add("payload.exe", b"fake binary executable content")
    pdf_bytes = doc.tobytes()
    doc.close()

    is_secure, reason = validate_pdf_security(pdf_bytes)
    assert is_secure is False
    assert "EmbeddedFiles" in (reason or "") or "adjuntos" in (reason or "").lower()


def test_corrupted_pdf_rejected():
    corrupted_bytes = b"%PDF-1.4 \xff\xfe\x00\x00 This is corrupted binary junk"
    is_secure, reason = validate_pdf_security(corrupted_bytes)
    assert is_secure is False
    assert "corrupto" in (reason or "").lower()
