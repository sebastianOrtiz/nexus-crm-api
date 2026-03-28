"""
Repository for Deal records.
"""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from src.models.deal import Deal
from src.models.deal_stage_history import DealStageHistory
from src.models.pipeline_stage import PipelineStage
from src.repositories.base import BaseRepository


class DealRepository(BaseRepository[Deal]):
    """Data-access layer for ``Deal`` records."""

    model = Deal

    async def get_by_id_and_org(
        self,
        record_id: UUID,
        organization_id: UUID,
    ) -> Deal | None:
        """
        Fetch a deal by ID scoped to a tenant, eagerly loading stage history.

        Overrides the base implementation to include the ``stage_history``
        collection along with each entry's ``stage`` and ``moved_by`` user,
        so the response schema can resolve ``stage_name`` and ``moved_by_name``
        without additional queries.

        Args:
            record_id: UUID primary key of the deal.
            organization_id: Tenant boundary UUID.

        Returns:
            The ``Deal`` ORM instance with ``stage_history`` populated,
            or ``None`` if not found within the tenant.
        """
        result = await self.session.execute(
            select(Deal)
            .where(
                Deal.id == record_id,
                Deal.organization_id == organization_id,
            )
            .options(
                joinedload(Deal.stage),
                joinedload(Deal.stage_history).options(
                    joinedload(DealStageHistory.stage),
                    joinedload(DealStageHistory.moved_by),
                ),
            )
        )
        return result.unique().scalar_one_or_none()

    async def list_by_org(
        self,
        organization_id: UUID,
        *,
        stage_id: UUID | None = None,
        assigned_to_id: UUID | None = None,
        contact_id: UUID | None = None,
        company_id: UUID | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Deal], int]:
        """
        Paginated, filterable list of deals for one tenant.

        Args:
            organization_id: Tenant boundary UUID.
            stage_id: Optional filter by pipeline stage.
            assigned_to_id: Optional filter by assigned user.
            contact_id: Optional filter by related contact.
            company_id: Optional filter by related company.
            offset: Rows to skip.
            limit: Maximum rows to return.

        Returns:
            ``(deals, total)`` tuple.
        """
        base_q = select(Deal).where(Deal.organization_id == organization_id)

        if stage_id is not None:
            base_q = base_q.where(Deal.stage_id == stage_id)
        if assigned_to_id is not None:
            base_q = base_q.where(Deal.assigned_to_id == assigned_to_id)
        if contact_id is not None:
            base_q = base_q.where(Deal.contact_id == contact_id)
        if company_id is not None:
            base_q = base_q.where(Deal.company_id == company_id)

        count_result = await self.session.execute(
            select(func.count()).select_from(base_q.subquery())
        )
        total: int = count_result.scalar_one()

        items_result = await self.session.execute(
            base_q.options(joinedload(Deal.stage))
            .order_by(Deal.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(items_result.unique().scalars().all()), total

    async def pipeline_stats(self, organization_id: UUID) -> list[dict]:
        """
        Aggregate deal counts and values grouped by pipeline stage.

        Used by the dashboard pipeline endpoint.

        Args:
            organization_id: Tenant boundary UUID.

        Returns:
            List of dicts with keys: ``stage_id``, ``stage_name``,
            ``deal_count``, ``total_value``.
        """
        result = await self.session.execute(
            select(
                PipelineStage.id.label("stage_id"),
                PipelineStage.name.label("stage_name"),
                func.count(Deal.id).label("deal_count"),
                func.coalesce(func.sum(Deal.value), 0).label("total_value"),
            )
            .join(Deal, Deal.stage_id == PipelineStage.id, isouter=True)
            .where(PipelineStage.organization_id == organization_id)
            .group_by(PipelineStage.id, PipelineStage.name, PipelineStage.order)
            .order_by(PipelineStage.order)
        )
        return [row._asdict() for row in result.all()]
