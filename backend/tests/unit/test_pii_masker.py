"""
Unit tests for PII masking (Habeas Data & Ley 1581 de 2012 compliance).
"""

from app.infrastructure.security.pii_masker import (
    mask_email,
    mask_identification,
    mask_person_pii,
    mask_phone,
)


def test_mask_identification_colombian_cedula():
    assert mask_identification("1037648902") == "1037***902"
    assert mask_identification("71234567") == "7123***567"
    assert mask_identification("1234567") == "12***67"
    assert mask_identification("1234") == "****"
    assert mask_identification(None) is None
    assert mask_identification("") is None


def test_mask_email():
    assert mask_email("carolina.marin@example.com") == "c***n@example.com"
    assert mask_email("ab@empresa.gov.co") == "a*@empresa.gov.co"
    assert mask_email("x@test.com") == "x*@test.com"
    assert mask_email("invalid-email") == "invalid-email"
    assert mask_email(None) is None


def test_mask_phone():
    assert mask_phone("3123456789") == "312****789"
    assert mask_phone("+573123456789") == "+57****789"
    assert mask_phone("6042345678") == "604****678"
    assert mask_phone("1234") == "****"
    assert mask_phone(None) is None


def test_mask_person_pii():
    person_data = {
        "id": "abc-123",
        "first_name": "Carolina",
        "identification_number": "1037648902",
        "email": "carolina@mail.com",
        "telephone": "6042345678",
        "mobile_phone": "3123456789",
    }

    masked = mask_person_pii(person_data)

    assert masked["first_name"] == "Carolina"
    assert masked["identification_number"] == "1037***902"
    assert masked["email"] == "c***a@mail.com"
    assert masked["telephone"] == "604****678"
    assert masked["mobile_phone"] == "312****789"
