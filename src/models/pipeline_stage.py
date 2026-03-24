"""
PipelineStage model — an ordered step in a sales pipeline.
"""

import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import SCHEMA, Base, UUIDMixin


class PipelineStage(UUIDMixin, Base):
    """
    A single stage in an organization's sales pipeline.

    Stages are ordered and at most one can be marked ``is_won`` and one
    ``is_lost``.  Those flags drive won/lost reporting in the dashboard.

    Attributes:
        id: Primary key UUID.
        organization_id: Tenant boundary FK.
        name: Display name of the stage (e.g., ``"Qualified"``).
        order: Sort position; lower numbers appear first in the funnel.
        is_won: True for the stage that marks a deal as closed-won.
        is_lost: True for the stage that marks a deal as closed-lost.
    """

    __tablename__ = "pipeline_stages"
    __table_args__ = {"schema": SCHEMA}

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_won: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_lost: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Relationships
    organization: Mapped["Organization"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Organization",
        back_populates="pipeline_stages",
        lazy="noload",
    )
    deals: Mapped[list["Deal"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Deal",
        back_populates="stage",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<PipelineStage id={self.id} name={self.name!r} order={self.order}>"
