"""
User model — a member of an organization with a specific role.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.enums import UserRole
from src.models.base import SCHEMA, Base, UUIDMixin


class User(UUIDMixin, Base):
    """
    A CRM user that belongs to a single organization.

    Attributes:
        id: Primary key UUID.
        organization_id: FK to the owning organization (tenant boundary).
        email: Unique e-mail address used for login.
        password_hash: bcrypt hash of the user's password.
        first_name: Given name.
        last_name: Family name.
        role: Permission level within the organization.
        is_active: Soft-delete flag.
        created_at: UTC creation timestamp.
    """

    __tablename__ = "users"
    __table_args__ = {"schema": SCHEMA}

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=UserRole.SALES_REP.value,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Organization",
        back_populates="users",
        lazy="noload",
    )
    assigned_contacts: Mapped[list["Contact"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Contact",
        foreign_keys="Contact.assigned_to_id",
        back_populates="assigned_to",
        lazy="noload",
    )
    assigned_deals: Mapped[list["Deal"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Deal",
        foreign_keys="Deal.assigned_to_id",
        back_populates="assigned_to",
        lazy="noload",
    )
    activities: Mapped[list["Activity"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Activity",
        back_populates="user",
        lazy="noload",
    )

    @property
    def full_name(self) -> str:
        """Return the concatenated first and last name."""
        return f"{self.first_name} {self.last_name}"

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r} role={self.role!r}>"
