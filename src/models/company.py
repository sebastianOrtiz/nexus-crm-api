"""
Company model — a business entity that can be linked to contacts and deals.
"""

import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import SCHEMA, Base, TimestampMixin, UUIDMixin


class Company(UUIDMixin, TimestampMixin, Base):
    """
    A business/company tracked in the CRM.

    Attributes:
        id: Primary key UUID.
        organization_id: Tenant boundary FK.
        name: Company name.
        domain: Web domain (e.g., ``"acme.com"``), optional.
        industry: Business sector, optional.
        phone: Main phone number, optional.
        address: Full address string, optional.
        notes: Free-text notes, optional.
        created_at: UTC creation timestamp.
        updated_at: UTC last-modified timestamp.
    """

    __tablename__ = "companies"
    __table_args__ = {"schema": SCHEMA}

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(100), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    organization: Mapped["Organization"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Organization",
        back_populates="companies",
        lazy="noload",
    )
    contacts: Mapped[list["Contact"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Contact",
        back_populates="company",
        lazy="noload",
    )
    deals: Mapped[list["Deal"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Deal",
        back_populates="company",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<Company id={self.id} name={self.name!r}>"
