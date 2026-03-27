"""
Repository for dashboard aggregate queries.

These queries are read-only aggregations that span multiple tables. Keeping
them in a dedicated repository avoids polluting the entity repositories with
analytics concerns (Single Responsibility Principle).
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select

from src.models.company import Company
from src.models.contact import Contact
from src.models.deal import Deal
from src.models.pipeline_stage import PipelineStage


class DashboardRepository:
    """
    Read-only repository providing aggregated data for dashboard endpoints.

    Args:
        session: The async database session for the current request.
    """

    def __init__(self, session) -> None:  # type: ignore[no-untyped-def]
        self.session = session

    async def get_stats(self, organization_id: UUID, month_start: datetime) -> dict:
        """
        Compute KPI numbers for the dashboard header cards.

        Args:
            organization_id: Tenant boundary UUID.
            month_start: UTC start of the current calendar month.

        Returns:
            Dict with keys: open_deals, total_pipeline_value, won_deals_this_month,
            revenue_this_month, total_contacts, total_companies.
        """
        # Open deals (not in a won or lost stage)
        open_q = (
            select(func.count(Deal.id), func.coalesce(func.sum(Deal.value), 0))
            .join(PipelineStage, Deal.stage_id == PipelineStage.id)
            .where(
                Deal.organization_id == organization_id,
                PipelineStage.is_won.is_(False),
                PipelineStage.is_lost.is_(False),
            )
        )
        open_result = await self.session.execute(open_q)
        open_row = open_result.one()
        open_deals: int = open_row[0]
        total_pipeline_value: float = float(open_row[1])

        # Won deals this month
        won_q = (
            select(func.count(Deal.id), func.coalesce(func.sum(Deal.value), 0))
            .join(PipelineStage, Deal.stage_id == PipelineStage.id)
            .where(
                Deal.organization_id == organization_id,
                PipelineStage.is_won.is_(True),
                Deal.closed_at >= month_start,
            )
        )
        won_result = await self.session.execute(won_q)
        won_row = won_result.one()
        won_deals_this_month: int = won_row[0]
        revenue_this_month: float = float(won_row[1])

        # Contact count
        contact_count_result = await self.session.execute(
            select(func.count(Contact.id)).where(Contact.organization_id == organization_id)
        )
        total_contacts: int = contact_count_result.scalar_one()

        # Company count
        company_count_result = await self.session.execute(
            select(func.count(Company.id)).where(Company.organization_id == organization_id)
        )
        total_companies: int = company_count_result.scalar_one()

        return {
            "open_deals": open_deals,
            "total_pipeline_value": total_pipeline_value,
            "won_deals_this_month": won_deals_this_month,
            "revenue_this_month": revenue_this_month,
            "total_contacts": total_contacts,
            "total_companies": total_companies,
        }

    async def get_revenue_by_month(self, organization_id: UUID, months: int = 6) -> list[dict]:
        """
        Revenue aggregated by calendar month for the past N months.

        Args:
            organization_id: Tenant boundary UUID.
            months: How many past months to include.

        Returns:
            List of dicts with keys: ``period``, ``revenue``, ``deal_count``.
        """
        period_expr = func.to_char(Deal.closed_at, "YYYY-MM")
        result = await self.session.execute(
            select(
                period_expr.label("period"),
                func.coalesce(func.sum(Deal.value), 0).label("revenue"),
                func.count(Deal.id).label("deal_count"),
            )
            .join(PipelineStage, Deal.stage_id == PipelineStage.id)
            .where(
                Deal.organization_id == organization_id,
                PipelineStage.is_won.is_(True),
                Deal.closed_at.isnot(None),
            )
            .group_by(period_expr)
            .order_by(period_expr.desc())
            .limit(months)
        )
        return [row._asdict() for row in result.all()]
