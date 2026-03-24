"""
Pydantic schemas for the Deal resource.
"""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from src.core.enums import DealCurrency
from src.schemas.common import CamelModel


class DealResponse(CamelModel):
    """Full deal representation returned to clients."""

    id: UUID
    organization_id: UUID
    title: str
    value: float | None
    currency: DealCurrency
    stage_id: UUID
    contact_id: UUID | None
    company_id: UUID | None
    assigned_to_id: UUID | None
    expected_close: datetime | None
    closed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class DealCreate(CamelModel):
    """Payload for ``POST /api/v1/deals``."""

    title: str = Field(min_length=1, max_length=255)
    value: float | None = Field(default=None, ge=0)
    currency: DealCurrency = DealCurrency.USD
    stage_id: UUID
    contact_id: UUID | None = None
    company_id: UUID | None = None
    assigned_to_id: UUID | None = None
    expected_close: datetime | None = None


class DealUpdate(CamelModel):
    """Partial update payload for ``PUT /api/v1/deals/{id}``."""

    title: str | None = Field(default=None, min_length=1, max_length=255)
    value: float | None = Field(default=None, ge=0)
    currency: DealCurrency | None = None
    stage_id: UUID | None = None
    contact_id: UUID | None = None
    company_id: UUID | None = None
    assigned_to_id: UUID | None = None
    expected_close: datetime | None = None


class DealMoveStage(CamelModel):
    """Payload for ``PUT /api/v1/deals/{id}/stage``."""

    stage_id: UUID
