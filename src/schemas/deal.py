"""
Pydantic schemas for the Deal resource.
"""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from src.core.enums import DealCurrency
from src.schemas.common import CamelModel


class DealStageHistoryResponse(CamelModel):
    """
    Represents a single pipeline stage transition for a deal.

    ``stage_name`` and ``moved_by_name`` are resolved from the ORM
    relationships at query time — they are not stored as denormalised strings.

    Attributes:
        id: Primary key of the history entry.
        stage_id: UUID of the pipeline stage entered.
        stage_name: Display name of that stage.
        moved_by_name: Full name of the user who triggered the move.
        entered_at: When the deal entered this stage.
        exited_at: When the deal left this stage; ``None`` if still current.
    """

    id: UUID
    stage_id: UUID
    stage_name: str
    moved_by_name: str
    entered_at: datetime
    exited_at: datetime | None


class DealResponse(CamelModel):
    """Full deal representation returned to clients."""

    id: UUID
    organization_id: UUID
    title: str
    value: float | None
    currency: DealCurrency
    stage_id: UUID
    stage_name: str = ""
    status: str = "open"
    contact_id: UUID | None
    company_id: UUID | None
    assigned_to_id: UUID | None
    expected_close: datetime | None
    closed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    stage_history: list[DealStageHistoryResponse] = []


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
