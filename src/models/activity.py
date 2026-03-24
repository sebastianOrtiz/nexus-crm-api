"""
Activity model — a logged interaction (call, email, meeting, note).
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.enums import ActivityType
from src.models.base import SCHEMA, Base, UUIDMixin


class Activity(UUIDMixin, Base):
    """
    A CRM activity representing an interaction with a contact or deal.

    Attributes:
        id: Primary key UUID.
        organization_id: Tenant boundary FK.
        type: Category of activity (call, email, meeting, note).
        subject: Short headline for the activity.
        description: Optional longer description or transcript.
        contact_id: Optional FK to the related contact.
        deal_id: Optional FK to the related deal.
        user_id: FK to the user who logged or owns the activity.
        scheduled_at: When the activity is planned to happen.
        completed_at: When the activity was actually completed.
        created_at: UTC creation timestamp.
    """

    __tablename__ = "activities"
    __table_args__ = {"schema": SCHEMA}

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=ActivityType.NOTE.value,
    )
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    contact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.contacts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    deal_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.deals.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Organization",
        back_populates="activities",
        lazy="noload",
    )
    contact: Mapped[Optional["Contact"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Contact",
        back_populates="activities",
        lazy="noload",
    )
    deal: Mapped[Optional["Deal"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Deal",
        back_populates="activities",
        lazy="noload",
    )
    user: Mapped["User"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "User",
        back_populates="activities",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<Activity id={self.id} type={self.type!r} subject={self.subject!r}>"
