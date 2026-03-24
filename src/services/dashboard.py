"""
Dashboard service — aggregates KPI data for the dashboard endpoints.
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.activity import ActivityRepository
from src.repositories.dashboard import DashboardRepository
from src.repositories.deal import DealRepository
from src.schemas.dashboard import (
    ActivityStats,
    DashboardStats,
    PipelineStageStats,
    PipelineStats,
    RecentActivity,
    RevenueByPeriod,
    RevenueStats,
)


class DashboardService:
    """
    Aggregates data from multiple repositories to power dashboard endpoints.

    Args:
        session: Async database session.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._dash_repo = DashboardRepository(session)
        self._deal_repo = DealRepository(session)
        self._activity_repo = ActivityRepository(session)

    async def get_stats(self, organization_id: UUID) -> DashboardStats:
        """
        Compute KPI numbers for the dashboard header cards.

        Args:
            organization_id: Tenant boundary UUID.

        Returns:
            ``DashboardStats`` with open deals, pipeline value, revenue etc.
        """
        now = datetime.now(UTC)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        raw = await self._dash_repo.get_stats(organization_id, month_start)
        return DashboardStats(**raw)

    async def get_pipeline(self, organization_id: UUID) -> PipelineStats:
        """
        Return deal counts and values grouped by pipeline stage (funnel data).

        Args:
            organization_id: Tenant boundary UUID.

        Returns:
            ``PipelineStats`` with one entry per stage.
        """
        rows = await self._deal_repo.pipeline_stats(organization_id)
        stages = [
            PipelineStageStats(
                stage_id=str(row["stage_id"]),
                stage_name=row["stage_name"],
                deal_count=row["deal_count"],
                total_value=float(row["total_value"]),
            )
            for row in rows
        ]
        return PipelineStats(stages=stages)

    async def get_revenue(self, organization_id: UUID, months: int = 6) -> RevenueStats:
        """
        Return revenue aggregated by calendar month.

        Args:
            organization_id: Tenant boundary UUID.
            months: How many past months to include (default 6).

        Returns:
            ``RevenueStats`` with period-by-period revenue data.
        """
        rows = await self._dash_repo.get_revenue_by_month(organization_id, months)
        periods = [
            RevenueByPeriod(
                period=row["period"],
                revenue=float(row["revenue"]),
                deal_count=row["deal_count"],
            )
            for row in rows
        ]
        return RevenueStats(periods=periods)

    async def get_activity(self, organization_id: UUID) -> ActivityStats:
        """
        Return recent activity feed data.

        Args:
            organization_id: Tenant boundary UUID.

        Returns:
            ``ActivityStats`` with a recent feed and weekly count.
        """
        from datetime import timedelta

        now = datetime.now(UTC)
        week_start = now - timedelta(days=7)

        recent_items = await self._activity_repo.list_recent(organization_id, limit=10)
        total_this_week = await self._activity_repo.count_this_week(organization_id, week_start)

        recent = [
            RecentActivity(
                id=str(a.id),
                type=a.type,
                subject=a.subject,
                user_name=str(a.user_id),  # Will be enriched with join in future
                created_at=a.created_at.isoformat(),
            )
            for a in recent_items
        ]
        return ActivityStats(recent=recent, total_this_week=total_this_week)
