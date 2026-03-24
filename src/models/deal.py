"""
Deal model — a sales opportunity being tracked through the pipeline.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.enums import DealCurrency
from src.models.base import SCHEMA, Base, TimestampMixin, UUIDMixin


class Deal(UUIDMixin, TimestampMixin, Base):
    """
    A sales opportunity in the CRM.

    Attributes:
        id: Primary key UUID.
        organization_id: Tenant boundary FK.
        title: Short description of the opportunity.
        value: Monetary value of the deal.
        currency: ISO 4217 currency code.
        stage_id: FK to the current pipeline stage.
        contact_id: Optional FK to the primary contact.
        company_id: Optional FK to the related company.
        assigned_to_id: Optional FK to the responsible sales rep.
        expected_close: Expected close date, optional.
        closed_at: Actual close date (set when stage is won or lost).
        created_at: UTC creation timestamp.
        updated_at: UTC last-modified timestamp.
    """

    __tablename__ = "deals"
    __table_args__ = {"schema": SCHEMA}

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default=DealCurrency.USD.value,
    )
    stage_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.pipeline_stages.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    contact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.contacts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.companies.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    assigned_to_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    expected_close: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Organization",
        back_populates="deals",
        lazy="noload",
    )
    stage: Mapped["PipelineStage"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "PipelineStage",
        back_populates="deals",
        lazy="noload",
    )
    contact: Mapped[Optional["Contact"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Contact",
        back_populates="deals",
        lazy="noload",
    )
    company: Mapped[Optional["Company"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Company",
        back_populates="deals",
        lazy="noload",
    )
    assigned_to: Mapped[Optional["User"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "User",
        foreign_keys=[assigned_to_id],
        back_populates="assigned_deals",
        lazy="noload",
    )
    activities: Mapped[list["Activity"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Activity",
        back_populates="deal",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<Deal id={self.id} title={self.title!r} value={self.value}>"
