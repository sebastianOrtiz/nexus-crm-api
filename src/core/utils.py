"""
Shared utility helpers used across the application.

These are pure functions with no dependencies on frameworks or the database.
They live here — not in a service — because they encode no business rules,
only technical conventions.
"""


def normalize_email(email: str) -> str:
    """
    Normalize an email address to lowercase for consistent storage and lookup.

    Stripping surrounding whitespace before lowercasing prevents accidental
    duplicate accounts caused by copy-paste artefacts.

    Args:
        email: Raw email string as provided by the user.

    Returns:
        Cleaned, lowercase email string.
    """
    return email.strip().lower()
