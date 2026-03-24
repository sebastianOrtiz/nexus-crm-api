"""
Pydantic schemas for the Company resource.
"""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from src.schemas.common import CamelModel


class CompanyResponse(CamelModel):
    """Full company representation returned to clients."""

    id: UUID
    organization_id: UUID
    name: str
    domain: str | None
    industry: str | None
    phone: str | None
    address: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class CompanyCreate(CamelModel):
    """Payload for ``POST /api/v1/companies``."""

    name: str = Field(min_length=1, max_length=255)
    domain: str | None = Field(default=None, max_length=255)
    industry: str | None = Field(default=None, max_length=100)
    phone: str | None = Field(default=None, max_length=50)
    address: str | None = None
    notes: str | None = None


class CompanyUpdate(CamelModel):
    """Partial update payload for ``PUT /api/v1/companies/{id}``."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    domain: str | None = Field(default=None, max_length=255)
    industry: str | None = Field(default=None, max_length=100)
    phone: str | None = Field(default=None, max_length=50)
    address: str | None = None
    notes: str | None = None
