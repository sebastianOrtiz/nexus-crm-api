"""
Unit tests for DashboardService.

Mocks DashboardRepository, DealRepository, and ActivityRepository at the
instance level — no DB required.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.services.dashboard import DashboardService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _activity_item(activity_id=None, activity_type="call", subject="Test", user_id=None):
    from datetime import datetime

    return SimpleNamespace(
        id=activity_id or uuid4(),
        type=activity_type,
        subject=subject,
        user_id=user_id or uuid4(),
        created_at=datetime(2024, 1, 1),
    )


@pytest.fixture
def mock_session():
    return AsyncMock()


@pytest.fixture
def service(mock_session):
    svc = DashboardService(mock_session)
    svc._dash_repo = MagicMock()
    svc._deal_repo = MagicMock()
    svc._activity_repo = MagicMock()
    return svc


# ---------------------------------------------------------------------------
# get_stats
# ---------------------------------------------------------------------------


class TestGetStats:
    async def test_returns_dashboard_stats(self, service):
        org_id = uuid4()
        raw = {
            "open_deals": 5,
            "total_pipeline_value": 50000.0,
            "won_deals_this_month": 2,
            "revenue_this_month": 20000.0,
            "total_contacts": 100,
            "total_companies": 20,
        }
        service._dash_repo.get_stats = AsyncMock(return_value=raw)

        result = await service.get_stats(org_id)

        assert result.open_deals == 5
        assert result.total_pipeline_value == 50000.0
        assert result.won_deals_this_month == 2
        assert result.revenue_this_month == 20000.0
        assert result.total_contacts == 100
        assert result.total_companies == 20

    async def test_repo_is_called_with_org_id(self, service):
        org_id = uuid4()
        service._dash_repo.get_stats = AsyncMock(
            return_value={
                "open_deals": 0,
                "total_pipeline_value": 0.0,
                "won_deals_this_month": 0,
                "revenue_this_month": 0.0,
                "total_contacts": 0,
                "total_companies": 0,
            }
        )

        await service.get_stats(org_id)

        call_args = service._dash_repo.get_stats.call_args
        assert call_args.args[0] == org_id


# ---------------------------------------------------------------------------
# get_pipeline
# ---------------------------------------------------------------------------


class TestGetPipeline:
    async def test_returns_pipeline_stats_with_stages(self, service):
        org_id = uuid4()
        stage_id = uuid4()
        service._deal_repo.pipeline_stats = AsyncMock(
            return_value=[
                {
                    "stage_id": stage_id,
                    "stage_name": "Prospecting",
                    "deal_count": 3,
                    "total_value": 15000.0,
                }
            ]
        )

        result = await service.get_pipeline(org_id)

        assert len(result.stages) == 1
        assert result.stages[0].stage_name == "Prospecting"
        assert result.stages[0].deal_count == 3
        assert result.stages[0].total_value == 15000.0

    async def test_returns_empty_stages_when_no_deals(self, service):
        service._deal_repo.pipeline_stats = AsyncMock(return_value=[])

        result = await service.get_pipeline(uuid4())

        assert result.stages == []


# ---------------------------------------------------------------------------
# get_revenue
# ---------------------------------------------------------------------------


class TestGetRevenue:
    async def test_returns_revenue_stats(self, service):
        org_id = uuid4()
        service._dash_repo.get_revenue_by_month = AsyncMock(
            return_value=[
                {"period": "2024-01", "revenue": 10000.0, "deal_count": 2},
                {"period": "2023-12", "revenue": 5000.0, "deal_count": 1},
            ]
        )

        result = await service.get_revenue(org_id, months=6)

        assert len(result.periods) == 2
        assert result.periods[0].period == "2024-01"
        assert result.periods[0].revenue == 10000.0
        assert result.periods[1].deal_count == 1

    async def test_months_param_is_forwarded(self, service):
        service._dash_repo.get_revenue_by_month = AsyncMock(return_value=[])

        await service.get_revenue(uuid4(), months=3)

        call_args = service._dash_repo.get_revenue_by_month.call_args
        assert call_args.args[1] == 3

    async def test_returns_empty_periods_when_no_data(self, service):
        service._dash_repo.get_revenue_by_month = AsyncMock(return_value=[])

        result = await service.get_revenue(uuid4())

        assert result.periods == []


# ---------------------------------------------------------------------------
# get_activity
# ---------------------------------------------------------------------------


class TestGetActivity:
    async def test_returns_activity_stats(self, service):
        org_id = uuid4()
        items = [_activity_item() for _ in range(3)]
        service._activity_repo.list_recent = AsyncMock(return_value=items)
        service._activity_repo.count_this_week = AsyncMock(return_value=7)

        result = await service.get_activity(org_id)

        assert result.total_this_week == 7
        assert len(result.recent) == 3

    async def test_recent_activity_has_correct_fields(self, service):
        org_id = uuid4()
        item = _activity_item(activity_type="email", subject="Important email")
        service._activity_repo.list_recent = AsyncMock(return_value=[item])
        service._activity_repo.count_this_week = AsyncMock(return_value=1)

        result = await service.get_activity(org_id)

        recent = result.recent[0]
        assert recent.type == "email"
        assert recent.subject == "Important email"

    async def test_returns_empty_recent_when_no_activities(self, service):
        service._activity_repo.list_recent = AsyncMock(return_value=[])
        service._activity_repo.count_this_week = AsyncMock(return_value=0)

        result = await service.get_activity(uuid4())

        assert result.recent == []
        assert result.total_this_week == 0
