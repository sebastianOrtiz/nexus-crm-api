"""
Repository for PipelineStage records.
"""

from uuid import UUID

from sqlalchemy import select

from src.models.pipeline_stage import PipelineStage
from src.repositories.base import BaseRepository


class PipelineStageRepository(BaseRepository[PipelineStage]):
    """Data-access layer for ``PipelineStage`` records."""

    model = PipelineStage

    async def list_by_org_ordered(self, organization_id: UUID) -> list[PipelineStage]:
        """
        Return all pipeline stages for a tenant, sorted by display order.

        Args:
            organization_id: Tenant boundary UUID.

        Returns:
            Ordered list of ``PipelineStage`` instances.
        """
        result = await self.session.execute(
            select(PipelineStage)
            .where(PipelineStage.organization_id == organization_id)
            .order_by(PipelineStage.order)
        )
        return list(result.scalars().all())

    async def count_by_org(self, organization_id: UUID) -> int:
        """
        Return the total number of stages for a tenant.

        Used to auto-assign the next ``order`` value when creating a stage.

        Args:
            organization_id: Tenant boundary UUID.

        Returns:
            Stage count.
        """
        stages = await self.list_by_org_ordered(organization_id)
        return len(stages)
