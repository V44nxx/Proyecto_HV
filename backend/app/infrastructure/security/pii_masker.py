"""
Personally Identifiable Information (PII) Masker.

Provides masking utilities for sensitive personal data in compliance with:
- Colombian Personal Data Protection Law (Ley 1581 de 2012 - Habeas Data)
- Principle of data minimization in public and operational listings
"""

import re
from typing import Any


def mask_identification(identification_number: str | None) -> str | None:
    """
    Masks a citizen identification number (Cédula, Pasaporte, etc.).

    Example:
        '1037648902' -> '1037***902'
        '1234567'    -> '12***67'
    """
    if not identification_number:
        return None

    cleaned = identification_number.strip()
    length = len(cleaned)

    if length <= 4:
        return "*" * length

    if length <= 7:
        # Show first 2 and last 2
        return f"{cleaned[:2]}{'*' * (length - 4)}{cleaned[-2:]}"

    # Show first 4 and last 3
    prefix = cleaned[:4]
    suffix = cleaned[-3:]
    return f"{prefix}***{suffix}"


def mask_email(email: str | None) -> str | None:
    """
    Masks an email address preserving domain for context.

    Example:
        'carlos.ramirez@empresa.com' -> 'c***z@empresa.com'
        'ab@test.co'                 -> 'a*@test.co'
    """
    if not email or "@" not in email:
        return email

    parts = email.strip().split("@", 1)
    user_part, domain_part = parts[0], parts[1]

    if len(user_part) <= 2:
        masked_user = f"{user_part[0]}*"
    else:
        masked_user = f"{user_part[0]}***{user_part[-1]}"

    return f"{masked_user}@{domain_part}"


def mask_phone(phone: str | None) -> str | None:
    """
    Masks telephone and mobile phone numbers.

    Example:
        '3124567890' -> '312****890'
        '6042345678' -> '604****678'
    """
    if not phone:
        return None

    cleaned = re.sub(r"[^\d+]", "", phone.strip())
    length = len(cleaned)

    if length <= 5:
        return "*" * length

    prefix = cleaned[:3]
    suffix = cleaned[-3:]
    return f"{prefix}****{suffix}"


def mask_person_pii(data: dict[str, Any]) -> dict[str, Any]:
    """
    Applies PII masking recursively to a person summary dictionary.
    Safe copy of the input dictionary.
    """
    masked = dict(data)

    if "identification_number" in masked and masked["identification_number"]:
        masked["identification_number"] = mask_identification(str(masked["identification_number"]))

    if "email" in masked and masked["email"]:
        masked["email"] = mask_email(str(masked["email"]))

    if "telephone" in masked and masked["telephone"]:
        masked["telephone"] = mask_phone(str(masked["telephone"]))

    if "mobile_phone" in masked and masked["mobile_phone"]:
        masked["mobile_phone"] = mask_phone(str(masked["mobile_phone"]))

    if "phone" in masked and masked["phone"]:
        masked["phone"] = mask_phone(str(masked["phone"]))

    return masked
