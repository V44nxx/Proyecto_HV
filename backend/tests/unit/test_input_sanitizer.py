"""
Unit tests for input sanitization and injection defense.
"""

from app.infrastructure.security.input_sanitizer import (
    sanitize_filename,
    sanitize_html,
    sanitize_search_query,
)


def test_sanitize_html_removes_script_tags():
    raw = "<p>Hola</p><script>alert('XSS')</script><span>Mundo</span>"
    clean = sanitize_html(raw)
    assert "<script>" not in clean
    assert "alert" not in clean
    assert "Hola" in clean
    assert "Mundo" in clean


def test_sanitize_html_neutralizes_event_handlers():
    raw = '<img src="x" onerror="alert(1)" onload="evil()">'
    clean = sanitize_html(raw)
    assert "onerror=" not in clean
    assert "onload=" not in clean
    assert "data-sanitized=" in clean


def test_sanitize_html_removes_null_bytes():
    raw = "Texto con\x00 byte nulo"
    clean = sanitize_html(raw)
    assert "\x00" not in clean
    assert "Texto con byte nulo" == clean


def test_sanitize_html_empty():
    assert sanitize_html("") == ""
    assert sanitize_html(None) == ""


def test_sanitize_search_query_removes_sql_comments():
    query = "Carolina' OR 1=1 --"
    clean = sanitize_search_query(query)
    assert "--" not in clean
    assert "Carolina' OR 1=1" in clean


def test_sanitize_search_query_removes_union_select():
    query = "Medellín' UNION SELECT password FROM users;"
    clean = sanitize_search_query(query)
    assert "union select" not in clean.lower()


def test_sanitize_search_query_preserves_spanish_characters():
    query = "Bogotá, Medellín, Caquetá & Nariño"
    clean = sanitize_search_query(query)
    assert "Bogotá" in clean
    assert "Medellín" in clean
    assert "Nariño" in clean


def test_sanitize_search_query_limits_length():
    long_query = "A" * 500
    clean = sanitize_search_query(long_query, max_length=50)
    assert len(clean) == 50


def test_sanitize_filename_prevents_path_traversal():
    assert sanitize_filename("../../../etc/passwd") == "passwd"
    assert sanitize_filename("..\\..\\windows\\system32\\cmd.exe") == "cmd.exe"


def test_sanitize_filename_replaces_dangerous_characters():
    dirty = "reporte; rm -rf * | nc.pdf"
    clean = sanitize_filename(dirty)
    assert ";" not in clean
    assert "|" not in clean
    assert clean.endswith(".pdf")
