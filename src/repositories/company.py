"""
Repository for Company records.
"""

from uuid import UUID

from sqlalchemy import func, or_, select

from src.models.company import Company
from src.repositories.base import BaseRepository


class CompanyRepository(BaseRepository[Company]):
    """Data-access layer for ``Company`` records."""

    model = Company

    async def list_by_org(
        self,
        organization_id: UUID,
        *,
        search: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Company], int]:
        """
        Paginated, searchable list of companies for one tenant.

        Args:
            organization_id: Tenant boundary UUID.
            search: Optional substring to match against company name or domain.
            offset: Rows to skip.
            limit: Maximum rows to return.

        Returns:
            ``(companies, total)`` tuple.
        """
        base_q = select(Company).where(Company.organization_id == organization_id)

        if search:
            pattern = f"%{search}%"
            base_q = base_q.where(
                or_(
                    Company.name.ilike(pattern),
                    Company.domain.ilike(pattern),
                )
            )

        count_result = await self.session.execute(
            select(func.count()).select_from(base_q.subquery())
        )
        total: int = count_result.scalar_one()

        items_result = await self.session.execute(
            base_q.order_by(Company.name).offset(offset).limit(limit)
        )
        return list(items_result.scalars().all()), total
