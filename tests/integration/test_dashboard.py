"""
Integration tests for dashboard analytics endpoints.

All repository calls are mocked — no PostgreSQL required.

Tests cover:
- GET /api/v1/dashboard/stats    — DashboardStats structure
- GET /api/v1/dashboard/pipeline — PipelineStats structure
- GET /api/v1/dashboard/revenue  — RevenueStats structure
- GET /api/v1/dashboard/activity — ActivityStats structure
"""

from unittest.mock import AsyncMock, patch

from httpx import AsyncClient

from src.schemas.dashboard import (
    ActivityStats,
    DashboardStats,
    PipelineStats,
    RevenueStats,
)

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _make_dashboard_stats() -> DashboardStats:
    return DashboardStats(
        open_deals=5,
        total_pipeline_value=50000.0,
        won_deals_this_month=2,
        revenue_this_month=20000.0,
        total_contacts=42,
        total_companies=10,
    )


def _make_pipeline_stats() -> PipelineStats:
    return PipelineStats(stages=[])


def _make_revenue_stats() -> RevenueStats:
    return RevenueStats(periods=[])


def _make_activity_stats() -> ActivityStats:
    return ActivityStats(recent=[], total_this_week=7)


# ---------------------------------------------------------------------------
# GET /dashboard/stats
# ---------------------------------------------------------------------------


class TestDashboardStats:
    """GET /api/v1/dashboard/stats"""

    @patch("src.api.v1.routers.dashboard.DashboardService")
    async def test_stats_returns_200(
        self, mock_svc_cls: AsyncMock, client_owner: AsyncClient
    ) -> None:
        """Returns 200 with all required KPI fields."""
        mock_svc_cls.return_value.get_stats = AsyncMock(return_value=_make_dashboard_stats())

        response = await client_owner.get("/api/v1/dashboard/stats")

        assert response.status_code == 200
        data = response.json()
        assert "openDeals" in data
        assert "totalPipelineValue" in data
        assert "wonDealsThisMonth" in data
        assert "revenueThisMonth" in data
        assert "totalContacts" in data
        assert "totalCompanies" in data

    @patch("src.api.v1.routers.dashboard.DashboardService")
    async def test_stats_values(self, mock_svc_cls: AsyncMock, client_owner: AsyncClient) -> None:
        """Returned values match what the service produced."""
        stats = _make_dashboard_stats()
        mock_svc_cls.return_value.get_stats = AsyncMock(return_value=stats)

        response = await client_owner.get("/api/v1/dashboard/stats")

        data = response.json()
        assert data["openDeals"] == 5
        assert data["totalPipelineValue"] == 50000.0
        assert data["totalContacts"] == 42

    async def test_stats_unauthenticated(self, client_no_auth: AsyncClient) -> None:
        """Unauthenticated request returns 401."""
        response = await client_no_auth.get("/api/v1/dashboard/stats")
        assert response.status_code == 401

    @patch("src.api.v1.routers.dashboard.DashboardService")
    async def test_stats_accessible_by_viewer(
        self, mock_svc_cls: AsyncMock, client_viewer: AsyncClient
    ) -> None:
        """Viewer can access the dashboard (read-only)."""
        mock_svc_cls.return_value.get_stats = AsyncMock(return_value=_make_dashboard_stats())

        response = await client_viewer.get("/api/v1/dashboard/stats")

        assert response.status_code == 200


# ---------------------------------------------------------------------------
# GET /dashboard/pipeline
# ---------------------------------------------------------------------------


class TestDashboardPipeline:
    """GET /api/v1/dashboard/pipeline"""

    @patch("src.api.v1.routers.dashboard.DashboardService")
    async def test_pipeline_returns_200(
        self, mock_svc_cls: AsyncMock, client_owner: AsyncClient
    ) -> None:
        """Returns 200 with a list of pipeline stage stats."""
        mock_svc_cls.return_value.get_pipeline = AsyncMock(return_value=_make_pipeline_stats())

        response = await client_owner.get("/api/v1/dashboard/pipeline")

        assert response.status_code == 200
        assert "stages" in response.json()

    @patch("src.api.v1.routers.dashboard.DashboardService")
    async def test_pipeline_with_stages(
        self, mock_svc_cls: AsyncMock, client_owner: AsyncClient
    ) -> None:
        """Returns stage data when stages exist."""
        from src.schemas.dashboard import PipelineStageStats

        pipeline = PipelineStats(
            stages=[
                PipelineStageStats(
                    stage_id="stage-1",
                    stage_name="Prospecting",
                    deal_count=3,
                    total_value=30000.0,
                )
            ]
        )
        mock_svc_cls.return_value.get_pipeline = AsyncMock(return_value=pipeline)

        response = await client_owner.get("/api/v1/dashboard/pipeline")

        assert response.status_code == 200
        stages = response.json()["stages"]
        assert len(stages) == 1
        assert stages[0]["stageName"] == "Prospecting"
        assert stages[0]["dealCount"] == 3

    async def test_pipeline_unauthenticated(self, client_no_auth: AsyncClient) -> None:
        """Unauthenticated request returns 401."""
        response = await client_no_auth.get("/api/v1/dashboard/pipeline")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# GET /dashboard/revenue
# ---------------------------------------------------------------------------


class TestDashboardRevenue:
    """GET /api/v1/dashboard/revenue"""

    @patch("src.api.v1.routers.dashboard.DashboardService")
    async def test_revenue_returns_200(
        self, mock_svc_cls: AsyncMock, client_owner: AsyncClient
    ) -> None:
        """Returns 200 with a list of revenue periods."""
        mock_svc_cls.return_value.get_revenue = AsyncMock(return_value=_make_revenue_stats())

        response = await client_owner.get("/api/v1/dashboard/revenue")

        assert response.status_code == 200
        assert "periods" in response.json()

    @patch("src.api.v1.routers.dashboard.DashboardService")
    async def test_revenue_with_months_param(
        self, mock_svc_cls: AsyncMock, client_owner: AsyncClient
    ) -> None:
        """Accepts 'months' query parameter."""
        mock_svc_cls.return_value.get_revenue = AsyncMock(return_value=_make_revenue_stats())

        response = await client_owner.get("/api/v1/dashboard/revenue?months=3")

        assert response.status_code == 200
        mock_svc_cls.return_value.get_revenue.assert_called_once()

    @patch("src.api.v1.routers.dashboard.DashboardService")
    async def test_revenue_with_periods(
        self, mock_svc_cls: AsyncMock, client_owner: AsyncClient
    ) -> None:
        """Returns period data when revenue exists."""
        from src.schemas.dashboard import RevenueByPeriod

        revenue = RevenueStats(
            periods=[
                RevenueByPeriod(period="2026-01", revenue=10000.0, deal_count=2),
                RevenueByPeriod(period="2026-02", revenue=15000.0, deal_count=3),
            ]
        )
        mock_svc_cls.return_value.get_revenue = AsyncMock(return_value=revenue)

        response = await client_owner.get("/api/v1/dashboard/revenue")

        assert response.status_code == 200
        periods = response.json()["periods"]
        assert len(periods) == 2
        assert periods[0]["period"] == "2026-01"

    async def test_revenue_invalid_months_param(self, client_owner: AsyncClient) -> None:
        """months=0 is below the minimum (ge=1) — returns 422."""
        response = await client_owner.get("/api/v1/dashboard/revenue?months=0")
        assert response.status_code == 422

    async def test_revenue_unauthenticated(self, client_no_auth: AsyncClient) -> None:
        """Unauthenticated request returns 401."""
        response = await client_no_auth.get("/api/v1/dashboard/revenue")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# GET /dashboard/activity
# ---------------------------------------------------------------------------


class TestDashboardActivity:
    """GET /api/v1/dashboard/activity"""

    @patch("src.api.v1.routers.dashboard.DashboardService")
    async def test_activity_returns_200(
        self, mock_svc_cls: AsyncMock, client_owner: AsyncClient
    ) -> None:
        """Returns 200 with recent feed and weekly count."""
        mock_svc_cls.return_value.get_activity = AsyncMock(return_value=_make_activity_stats())

        response = await client_owner.get("/api/v1/dashboard/activity")

        assert response.status_code == 200
        data = response.json()
        assert "recent" in data
        assert "totalThisWeek" in data

    @patch("src.api.v1.routers.dashboard.DashboardService")
    async def test_activity_with_feed_entries(
        self, mock_svc_cls: AsyncMock, client_owner: AsyncClient
    ) -> None:
        """Returns feed entries when activities exist."""
        from src.schemas.dashboard import RecentActivity

        stats = ActivityStats(
            recent=[
                RecentActivity(
                    id="act-1",
                    type="call",
                    subject="Follow-up",
                    user_name="Jane",
                    created_at="2026-03-24T10:00:00",
                )
            ],
            total_this_week=5,
        )
        mock_svc_cls.return_value.get_activity = AsyncMock(return_value=stats)

        response = await client_owner.get("/api/v1/dashboard/activity")

        assert response.status_code == 200
        data = response.json()
        assert len(data["recent"]) == 1
        assert data["totalThisWeek"] == 5

    async def test_activity_unauthenticated(self, client_no_auth: AsyncClient) -> None:
        """Unauthenticated request returns 401."""
        response = await client_no_auth.get("/api/v1/dashboard/activity")
        assert response.status_code == 401
