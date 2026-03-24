"""
Pydantic schemas for the PipelineStage resource.
"""

from uuid import UUID

from pydantic import Field

from src.schemas.common import CamelModel


class PipelineStageResponse(CamelModel):
    """Full pipeline stage representation."""

    id: UUID
    organization_id: UUID
    name: str
    order: int
    is_won: bool
    is_lost: bool


class PipelineStageCreate(CamelModel):
    """Payload for ``POST /api/v1/pipeline-stages``."""

    name: str = Field(min_length=1, max_length=100)
    order: int = Field(default=0, ge=0)
    is_won: bool = False
    is_lost: bool = False


class PipelineStageUpdate(CamelModel):
    """Partial update payload for ``PUT /api/v1/pipeline-stages/{id}``."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    order: int | None = Field(default=None, ge=0)
    is_won: bool | None = None
    is_lost: bool | None = None
