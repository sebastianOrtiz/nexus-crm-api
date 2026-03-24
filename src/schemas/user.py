"""
Pydantic schemas for the User resource.
"""

from datetime import datetime
from uuid import UUID

from pydantic import EmailStr, Field

from src.core.enums import UserRole
from src.schemas.common import CamelModel


class UserResponse(CamelModel):
    """User representation returned to clients (never includes password_hash)."""

    id: UUID
    organization_id: UUID
    email: str
    first_name: str
    last_name: str
    role: UserRole
    is_active: bool
    created_at: datetime

    @property
    def full_name(self) -> str:
        """Concatenated first and last name."""
        return f"{self.first_name} {self.last_name}"


class UserCreate(CamelModel):
    """
    Payload to invite/create a new user inside an organization.

    Used by owners and admins on ``POST /api/v1/users``.
    """

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    role: UserRole = UserRole.SALES_REP


class UserUpdate(CamelModel):
    """Partial update payload for ``PUT /api/v1/users/{id}``."""

    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    role: UserRole | None = None
    is_active: bool | None = None


class UserMeUpdate(CamelModel):
    """Allows a user to update their own non-sensitive profile fields."""

    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
