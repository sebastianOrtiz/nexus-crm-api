"""
Pydantic schemas for the Organization resource.
"""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from src.core.enums import OrganizationPlan
from src.schemas.common import CamelModel


class OrganizationResponse(CamelModel):
    """Full organization representation returned to clients."""

    id: UUID
    name: str
    slug: str
    plan: OrganizationPlan
    is_active: bool
    created_at: datetime
    updated_at: datetime


class OrganizationUpdate(CamelModel):
    """
    Fields that an ``owner`` may update on their organization.

    All fields are optional — only provided fields are changed (PATCH semantics
    despite the route using PUT for simplicity).
    """

    name: str | None = Field(default=None, min_length=2, max_length=255)
    plan: OrganizationPlan | None = None
