"""
Organization model — the top-level tenant entity.

Every other record in the CRM is scoped to an organization via
``organization_id``, making the data model strictly multi-tenant.
"""

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.enums import OrganizationPlan
from src.models.base import SCHEMA, Base, TimestampMixin, UUIDMixin


class Organization(UUIDMixin, TimestampMixin, Base):
    """
    Represents a tenant (customer account) in the CRM.

    Attributes:
        id: Primary key UUID.
        name: Human-readable organization name.
        slug: URL-safe unique identifier used in API paths.
        plan: Subscription tier (free, starter, professional, enterprise).
        is_active: Soft-disable flag; deactivated orgs cannot authenticate.
        created_at: UTC timestamp of creation.
        updated_at: UTC timestamp of last modification.
    """

    __tablename__ = "organizations"
    __table_args__ = {"schema": SCHEMA}

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    plan: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=OrganizationPlan.FREE.value,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships — back-populated lazily to avoid circular imports
    users: Mapped[list["User"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "User",
        back_populates="organization",
        lazy="noload",
    )
    contacts: Mapped[list["Contact"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Contact",
        back_populates="organization",
        lazy="noload",
    )
    companies: Mapped[list["Company"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Company",
        back_populates="organization",
        lazy="noload",
    )
    pipeline_stages: Mapped[list["PipelineStage"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "PipelineStage",
        back_populates="organization",
        lazy="noload",
    )
    deals: Mapped[list["Deal"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Deal",
        back_populates="organization",
        lazy="noload",
    )
    activities: Mapped[list["Activity"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Activity",
        back_populates="organization",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<Organization id={self.id} slug={self.slug!r}>"
