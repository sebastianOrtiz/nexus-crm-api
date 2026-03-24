"""
Contact model — an individual person tracked in the CRM.
"""

import uuid
from typing import Optional

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.enums import ContactSource
from src.models.base import SCHEMA, Base, TimestampMixin, UUIDMixin


class Contact(UUIDMixin, TimestampMixin, Base):
    """
    An individual person linked to an organization's CRM.

    Attributes:
        id: Primary key UUID.
        organization_id: Tenant boundary FK.
        company_id: Optional FK to the contact's employer.
        first_name: Given name.
        last_name: Family name.
        email: Optional e-mail address.
        phone: Optional phone number.
        position: Job title or role at their company.
        source: Acquisition channel (website, referral, etc.).
        notes: Free-text notes.
        assigned_to_id: Optional FK to the user responsible for this contact.
        created_at: UTC creation timestamp.
        updated_at: UTC last-modified timestamp.
    """

    __tablename__ = "contacts"
    __table_args__ = {"schema": SCHEMA}

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.companies.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    position: Mapped[str | None] = mapped_column(String(150), nullable=True)
    source: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        default=ContactSource.OTHER.value,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    assigned_to_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Organization",
        back_populates="contacts",
        lazy="noload",
    )
    company: Mapped[Optional["Company"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Company",
        back_populates="contacts",
        lazy="noload",
    )
    assigned_to: Mapped[Optional["User"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "User",
        foreign_keys=[assigned_to_id],
        back_populates="assigned_contacts",
        lazy="noload",
    )
    activities: Mapped[list["Activity"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Activity",
        back_populates="contact",
        lazy="noload",
    )
    deals: Mapped[list["Deal"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Deal",
        back_populates="contact",
        lazy="noload",
    )

    @property
    def full_name(self) -> str:
        """Return the concatenated first and last name."""
        return f"{self.first_name} {self.last_name}"

    def __repr__(self) -> str:
        return f"<Contact id={self.id} name={self.full_name!r}>"
