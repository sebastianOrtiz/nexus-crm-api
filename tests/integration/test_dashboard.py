"""
Integration tests for dashboard analytics endpoints.

Tests cover:
- GET /dashboard/stats — returns correct DashboardStats structure
- GET /dashboard/pipeline — returns PipelineStats with per-stage data
- GET /dashboard/revenue — returns RevenueStats with period data
- GET /dashboard/activity — returns ActivityStats with feed and weekly count
- Auth required for all endpoints
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.organization import Organization
from src.models.user import User


@pytest.mark.asyncio
class TestDashboardStats:
    """Tests for GET /api/v1/dashboard/stats."""

    async def test_stats_returns_correct_structure(
        self,
        client: AsyncClient,
        owner_headers: dict,
    ) -> None:
        """Stats endpoint returns all required KPI fields."""
        response = await client.get("/api/v1/dashboard/stats", headers=owner_headers)
        assert response.status_code == 200
        data = response.json()
        assert "openDeals" in data
        assert "totalPipelineValue" in data
        assert "wonDealsThisMonth" in data
        assert "revenueThisMonth" in data
        assert "totalContacts" in data
        assert "totalCompanies" in data

    async def test_stats_values_are_numeric(
        self,
        client: AsyncClient,
        owner_headers: dict,
    ) -> None:
        """All numeric KPI fields have the correct types."""
        response = await client.get("/api/v1/dashboard/stats", headers=owner_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["openDeals"], int)
        assert isinstance(data["totalPipelineValue"], int | float)
        assert isinstance(data["wonDealsThisMonth"], int)
        assert isinstance(data["revenueThisMonth"], int | float)
        assert isinstance(data["totalContacts"], int)
        assert isinstance(data["totalCompanies"], int)

    async def test_stats_requires_auth(self, client: AsyncClient) -> None:
        """Unauthenticated request returns 401."""
        response = await client.get("/api/v1/dashboard/stats")
        assert response.status_code == 401

    async def test_sales_rep_can_view_stats(
        self,
        client: AsyncClient,
        rep_headers: dict,
    ) -> None:
        """Sales reps have read access to the dashboard."""
        response = await client.get("/api/v1/dashboard/stats", headers=rep_headers)
        assert response.status_code == 200

    async def test_stats_reflect_created_contacts(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        org: Organization,
        owner_headers: dict,
    ) -> None:
        """total_contacts increments as contacts are added."""
        from datetime import UTC, datetime
        from uuid import uuid4

        from src.models.contact import Contact

        before = (await client.get("/api/v1/dashboard/stats", headers=owner_headers)).json()
        initial_count = before["totalContacts"]

        # Add a contact directly
        contact = Contact(
            organization_id=org.id,
            first_name="Stat",
            last_name="Contact",
            email=f"stat.{uuid4().hex[:6]}@test.com",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db_session.add(contact)
        await db_session.flush()

        after = (await client.get("/api/v1/dashboard/stats", headers=owner_headers)).json()
        assert after["totalContacts"] == initial_count + 1


@pytest.mark.asyncio
class TestDashboardPipeline:
    """Tests for GET /api/v1/dashboard/pipeline."""

    async def test_pipeline_returns_correct_structure(
        self,
        client: AsyncClient,
        owner_headers: dict,
    ) -> None:
        """Pipeline endpoint returns a stages list."""
        response = await client.get("/api/v1/dashboard/pipeline", headers=owner_headers)
        assert response.status_code == 200
        data = response.json()
        assert "stages" in data
        assert isinstance(data["stages"], list)

    async def test_pipeline_stage_has_required_fields(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        org: Organization,
        owner_headers: dict,
    ) -> None:
        """Each stage entry in the pipeline response has the required fields."""
        from src.models.pipeline_stage import PipelineStage

        stage = PipelineStage(
            organization_id=org.id,
            name="Pipeline Test Stage",
            order=99,
            is_won=False,
            is_lost=False,
        )
        db_session.add(stage)
        await db_session.flush()

        response = await client.get("/api/v1/dashboard/pipeline", headers=owner_headers)
        assert response.status_code == 200
        data = response.json()

        # Find the stage we just created
        matching = [s for s in data["stages"] if s["stageName"] == "Pipeline Test Stage"]
        assert len(matching) == 1
        s = matching[0]
        assert "stageId" in s
        assert "stageName" in s
        assert "dealCount" in s
        assert "totalValue" in s

    async def test_pipeline_requires_auth(self, client: AsyncClient) -> None:
        """Unauthenticated request returns 401."""
        response = await client.get("/api/v1/dashboard/pipeline")
        assert response.status_code == 401


@pytest.mark.asyncio
class TestDashboardRevenue:
    """Tests for GET /api/v1/dashboard/revenue."""

    async def test_revenue_returns_correct_structure(
        self,
        client: AsyncClient,
        owner_headers: dict,
    ) -> None:
        """Revenue endpoint returns a periods list."""
        response = await client.get("/api/v1/dashboard/revenue", headers=owner_headers)
        assert response.status_code == 200
        data = response.json()
        assert "periods" in data
        assert isinstance(data["periods"], list)

    async def test_revenue_period_has_required_fields(
        self,
        client: AsyncClient,
        owner_headers: dict,
    ) -> None:
        """Each period entry has the required fields when periods are present."""
        response = await client.get("/api/v1/dashboard/revenue", headers=owner_headers)
        assert response.status_code == 200
        data = response.json()

        for period in data["periods"]:
            assert "period" in period
            assert "revenue" in period
            assert "dealCount" in period

    async def test_revenue_months_parameter(
        self,
        client: AsyncClient,
        owner_headers: dict,
    ) -> None:
        """The months parameter is accepted without error."""
        response = await client.get(
            "/api/v1/dashboard/revenue",
            headers=owner_headers,
            params={"months": 3},
        )
        assert response.status_code == 200

    async def test_revenue_requires_auth(self, client: AsyncClient) -> None:
        """Unauthenticated request returns 401."""
        response = await client.get("/api/v1/dashboard/revenue")
        assert response.status_code == 401


@pytest.mark.asyncio
class TestDashboardActivity:
    """Tests for GET /api/v1/dashboard/activity."""

    async def test_activity_returns_correct_structure(
        self,
        client: AsyncClient,
        owner_headers: dict,
    ) -> None:
        """Activity endpoint returns the required fields."""
        response = await client.get("/api/v1/dashboard/activity", headers=owner_headers)
        assert response.status_code == 200
        data = response.json()
        assert "recent" in data
        assert "totalThisWeek" in data
        assert isinstance(data["recent"], list)
        assert isinstance(data["totalThisWeek"], int)

    async def test_activity_feed_entry_fields(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        org: Organization,
        owner_user: User,
        owner_headers: dict,
    ) -> None:
        """Recent activity feed entries have the required fields."""
        from datetime import UTC, datetime

        from src.models.activity import Activity

        activity = Activity(
            organization_id=org.id,
            user_id=owner_user.id,
            type="call",
            subject="Dashboard Feed Test",
            created_at=datetime.now(UTC),
        )
        db_session.add(activity)
        await db_session.flush()

        response = await client.get("/api/v1/dashboard/activity", headers=owner_headers)
        assert response.status_code == 200
        data = response.json()

        if data["recent"]:
            entry = data["recent"][0]
            assert "id" in entry
            assert "type" in entry
            assert "subject" in entry
            assert "userName" in entry
            assert "createdAt" in entry

    async def test_activity_requires_auth(self, client: AsyncClient) -> None:
        """Unauthenticated request returns 401."""
        response = await client.get("/api/v1/dashboard/activity")
        assert response.status_code == 401
