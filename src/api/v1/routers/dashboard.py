"""
Dashboard router — analytics and KPI endpoints.
"""

from fastapi import APIRouter, Query

from src.api.v1.dependencies import CurrentUser, DBSession
from src.schemas.dashboard import ActivityStats, DashboardStats, PipelineStats, RevenueStats
from src.services.dashboard import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get(
    "/stats",
    response_model=DashboardStats,
    summary="Get KPI stats",
)
async def get_stats(current_user: CurrentUser, session: DBSession) -> DashboardStats:
    """
    Return high-level KPI numbers for the dashboard header cards.

    Includes: open deals, pipeline value, won deals this month, revenue,
    total contacts and companies.

    Args:
        current_user: Injected authenticated user.
        session: Injected async database session.

    Returns:
        ``DashboardStats`` aggregate.
    """
    svc = DashboardService(session)
    return await svc.get_stats(current_user.organization_id)


@router.get(
    "/pipeline",
    response_model=PipelineStats,
    summary="Get pipeline funnel data",
)
async def get_pipeline(current_user: CurrentUser, session: DBSession) -> PipelineStats:
    """
    Return deal counts and values grouped by pipeline stage.

    Used to render the pipeline funnel chart on the dashboard.

    Args:
        current_user: Injected authenticated user.
        session: Injected async database session.

    Returns:
        ``PipelineStats`` with per-stage data.
    """
    svc = DashboardService(session)
    return await svc.get_pipeline(current_user.organization_id)


@router.get(
    "/revenue",
    response_model=RevenueStats,
    summary="Get revenue by period",
)
async def get_revenue(
    current_user: CurrentUser,
    session: DBSession,
    months: int = Query(default=6, ge=1, le=24),
) -> RevenueStats:
    """
    Return revenue aggregated by calendar month for the past N months.

    Args:
        current_user: Injected authenticated user.
        session: Injected async database session.
        months: Number of past months to include (default 6, max 24).

    Returns:
        ``RevenueStats`` with period-by-period data.
    """
    svc = DashboardService(session)
    return await svc.get_revenue(current_user.organization_id, months=months)


@router.get(
    "/activity",
    response_model=ActivityStats,
    summary="Get recent activity feed",
)
async def get_activity(current_user: CurrentUser, session: DBSession) -> ActivityStats:
    """
    Return the recent activity feed and weekly count.

    Args:
        current_user: Injected authenticated user.
        session: Injected async database session.

    Returns:
        ``ActivityStats`` with recent entries and weekly total.
    """
    svc = DashboardService(session)
    return await svc.get_activity(current_user.organization_id)
