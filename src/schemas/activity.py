"""
Pydantic schemas for the Activity resource.
"""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from src.core.enums import ActivityType
from src.schemas.common import CamelModel


class ActivityResponse(CamelModel):
    """Full activity representation returned to clients."""

    id: UUID
    organization_id: UUID
    type: ActivityType
    subject: str
    description: str | None
    contact_id: UUID | None
    deal_id: UUID | None
    user_id: UUID
    scheduled_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


class ActivityCreate(CamelModel):
    """Payload for ``POST /api/v1/activities``."""

    type: ActivityType
    subject: str = Field(min_length=1, max_length=255)
    description: str | None = None
    contact_id: UUID | None = None
    deal_id: UUID | None = None
    scheduled_at: datetime | None = None
    completed_at: datetime | None = None


class ActivityUpdate(CamelModel):
    """Partial update payload for ``PUT /api/v1/activities/{id}``."""

    type: ActivityType | None = None
    subject: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    contact_id: UUID | None = None
    deal_id: UUID | None = None
    scheduled_at: datetime | None = None
    completed_at: datetime | None = None
