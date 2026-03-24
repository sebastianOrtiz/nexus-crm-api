"""
Pydantic schemas for authentication endpoints.
"""

from pydantic import BaseModel, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    """
    Payload for ``POST /api/v1/auth/register``.

    Creates a new organization with the caller as the first ``owner`` user.
    """

    organization_name: str = Field(min_length=2, max_length=255)
    organization_slug: str = Field(
        min_length=2,
        max_length=100,
        pattern=r"^[a-z0-9-]+$",
        description="URL-safe slug: lowercase letters, digits and hyphens only",
    )
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        """Enforce at least one digit and one letter in the password."""
        has_letter = any(c.isalpha() for c in v)
        has_digit = any(c.isdigit() for c in v)
        if not (has_letter and has_digit):
            raise ValueError("Password must contain at least one letter and one digit")
        return v


class LoginRequest(BaseModel):
    """Payload for ``POST /api/v1/auth/login``."""

    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    """Payload for ``POST /api/v1/auth/refresh``."""

    refresh_token: str


class LogoutRequest(BaseModel):
    """Payload for ``POST /api/v1/auth/logout``."""

    refresh_token: str


class TokenResponse(BaseModel):
    """
    Response envelope for login and refresh operations.

    Attributes:
        access_token: Short-lived JWT for authorising resource requests.
        refresh_token: Long-lived JWT used to obtain new access tokens.
        token_type: Always ``"bearer"``.
    """

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
