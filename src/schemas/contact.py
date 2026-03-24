"""
Pydantic schemas for the Contact resource.
"""

from datetime import datetime
from uuid import UUID

from pydantic import EmailStr, Field

from src.core.enums import ContactSource
from src.schemas.common import CamelModel


class ContactResponse(CamelModel):
    """Full contact representation returned to clients."""

    id: UUID
    organization_id: UUID
    company_id: UUID | None
    first_name: str
    last_name: str
    email: str | None
    phone: str | None
    position: str | None
    source: ContactSource | None
    notes: str | None
    assigned_to_id: UUID | None
    created_at: datetime
    updated_at: datetime


class ContactCreate(CamelModel):
    """Payload for ``POST /api/v1/contacts``."""

    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    position: str | None = Field(default=None, max_length=150)
    source: ContactSource = ContactSource.OTHER
    notes: str | None = None
    company_id: UUID | None = None
    assigned_to_id: UUID | None = None


class ContactUpdate(CamelModel):
    """Partial update payload for ``PUT /api/v1/contacts/{id}``."""

    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    position: str | None = Field(default=None, max_length=150)
    source: ContactSource | None = None
    notes: str | None = None
    company_id: UUID | None = None
    assigned_to_id: UUID | None = None
