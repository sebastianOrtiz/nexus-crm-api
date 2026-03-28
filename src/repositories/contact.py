"""
Repository for Contact records.
"""

from uuid import UUID

from sqlalchemy import func, or_, select

from src.models.contact import Contact
from src.repositories.base import BaseRepository


class ContactRepository(BaseRepository[Contact]):
    """Data-access layer for ``Contact`` records."""

    model = Contact

    async def list_by_org(
        self,
        organization_id: UUID,
        *,
        search: str | None = None,
        source: str | None = None,
        company_id: UUID | None = None,
        assigned_to_id: UUID | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Contact], int]:
        """
        Paginated, filterable list of contacts for one tenant.

        Args:
            organization_id: Tenant boundary UUID.
            search: Optional substring to match name or email.
            company_id: Filter by company FK.
            assigned_to_id: Filter by assigned sales rep FK.
            offset: Rows to skip.
            limit: Maximum rows to return.

        Returns:
            ``(contacts, total)`` tuple.
        """
        base_q = select(Contact).where(Contact.organization_id == organization_id)

        if search:
            pattern = f"%{search}%"
            base_q = base_q.where(
                or_(
                    Contact.first_name.ilike(pattern),
                    Contact.last_name.ilike(pattern),
                    Contact.email.ilike(pattern),
                )
            )
        if source is not None:
            base_q = base_q.where(Contact.source == source)
        if company_id is not None:
            base_q = base_q.where(Contact.company_id == company_id)
        if assigned_to_id is not None:
            base_q = base_q.where(Contact.assigned_to_id == assigned_to_id)

        count_result = await self.session.execute(
            select(func.count()).select_from(base_q.subquery())
        )
        total: int = count_result.scalar_one()

        items_result = await self.session.execute(
            base_q.order_by(Contact.last_name, Contact.first_name).offset(offset).limit(limit)
        )
        return list(items_result.scalars().all()), total

    async def list_by_company(
        self,
        company_id: UUID,
        organization_id: UUID,
    ) -> list[Contact]:
        """
        Return all contacts that belong to a specific company within a tenant.

        Args:
            company_id: The company FK to filter by.
            organization_id: Tenant boundary UUID.

        Returns:
            List of ``Contact`` instances.
        """
        result = await self.session.execute(
            select(Contact).where(
                Contact.company_id == company_id,
                Contact.organization_id == organization_id,
            )
        )
        return list(result.scalars().all())
