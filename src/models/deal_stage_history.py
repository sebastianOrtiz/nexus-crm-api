"""
DealStageHistory model — audit trail of pipeline stage transitions for a deal.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import SCHEMA, Base, UUIDMixin


class DealStageHistory(UUIDMixin, Base):
    """
    Records every time a deal moves from one pipeline stage to another.

    An open entry (``exited_at`` is ``None``) indicates the deal is currently
    in that stage.  When the deal moves, the current entry is closed
    (``exited_at`` set to now) and a new open entry is created.

    Attributes:
        id: Primary key UUID.
        deal_id: FK to the deal this entry belongs to.
        stage_id: FK to the pipeline stage the deal entered.
        moved_by_id: FK to the user who performed the stage transition.
        entered_at: Timestamp when the deal entered this stage (UTC).
        exited_at: Timestamp when the deal left this stage; ``None`` while
            the deal remains in this stage.
    """

    __tablename__ = "deal_stage_history"
    __table_args__ = {"schema": SCHEMA}

    deal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.deals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stage_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.pipeline_stages.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    moved_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    entered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    exited_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    deal: Mapped["Deal"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Deal",
        back_populates="stage_history",
        lazy="noload",
    )
    stage: Mapped["PipelineStage"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "PipelineStage",
        lazy="noload",
    )
    moved_by: Mapped["User"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "User",
        lazy="noload",
    )

    @property
    def stage_name(self) -> str:
        """Return the name of the pipeline stage for this history entry."""
        return self.stage.name  # type: ignore[return-value]

    @property
    def moved_by_name(self) -> str:
        """Return the full name of the user who triggered this stage move."""
        return self.moved_by.full_name  # type: ignore[return-value]

    def __repr__(self) -> str:
        return (
            f"<DealStageHistory id={self.id} deal_id={self.deal_id}"
            f" stage_id={self.stage_id} entered_at={self.entered_at}>"
        )
