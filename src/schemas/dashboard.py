"""
Pydantic schemas for dashboard/analytics endpoints.
"""

from pydantic import BaseModel


class DashboardStats(BaseModel):
    """
    High-level KPI numbers for the dashboard header cards.

    Attributes:
        open_deals: Number of deals not in a won or lost stage.
        total_pipeline_value: Sum of values for all open deals.
        won_deals_this_month: Count of deals moved to a won stage this month.
        revenue_this_month: Sum of values for deals won this month.
        total_contacts: Total contacts in the organization.
        total_companies: Total companies in the organization.
    """

    open_deals: int
    total_pipeline_value: float
    won_deals_this_month: int
    revenue_this_month: float
    total_contacts: int
    total_companies: int


class PipelineStageStats(BaseModel):
    """Deal count and total value for a single pipeline stage."""

    stage_id: str
    stage_name: str
    deal_count: int
    total_value: float


class PipelineStats(BaseModel):
    """Funnel data: one entry per pipeline stage."""

    stages: list[PipelineStageStats]


class RevenueByPeriod(BaseModel):
    """Revenue aggregated by a calendar period (e.g., month)."""

    period: str
    """ISO-8601 period label, e.g. ``'2025-03'``."""
    revenue: float
    deal_count: int


class RevenueStats(BaseModel):
    """Revenue chart data for the past N periods."""

    periods: list[RevenueByPeriod]


class RecentActivity(BaseModel):
    """A single entry in the recent activity feed."""

    id: str
    type: str
    subject: str
    user_name: str
    created_at: str


class ActivityStats(BaseModel):
    """Activity feed data for the dashboard."""

    recent: list[RecentActivity]
    total_this_week: int
