"""
Unit tests for DealService.

Mocks DealRepository and PipelineStageRepository at the instance level.
"""

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.core.enums import DealCurrency, UserRole
from src.core.exceptions import ForbiddenError, NotFoundError
from src.schemas.deal import DealCreate, DealMoveStage, DealUpdate
from src.services.deal import DealService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _user(role: str, user_id=None):
    return SimpleNamespace(id=user_id or uuid4(), organization_id=uuid4(), role=role)


def _stage(org_id=None, is_won=False, is_lost=False):
    return SimpleNamespace(
        id=uuid4(),
        organization_id=org_id or uuid4(),
        name="Prospecting",
        order=1,
        is_won=is_won,
        is_lost=is_lost,
    )


def _deal(org_id=None, assigned_to_id=None, stage_id=None, closed_at=None):
    return SimpleNamespace(
        id=uuid4(),
        organization_id=org_id or uuid4(),
        title="Big Deal",
        value=10000.0,
        currency="USD",
        stage_id=stage_id or uuid4(),
        contact_id=None,
        company_id=None,
        assigned_to_id=assigned_to_id,
        expected_close=None,
        closed_at=closed_at,
        created_at=datetime(2024, 1, 1),
        updated_at=datetime(2024, 1, 1),
    )


@pytest.fixture
def mock_session():
    return AsyncMock()


@pytest.fixture
def service(mock_session):
    svc = DealService(mock_session)
    svc._repo = MagicMock()
    svc._stage_repo = MagicMock()
    return svc


# ---------------------------------------------------------------------------
# list_deals
# ---------------------------------------------------------------------------


class TestListDeals:
    async def test_owner_sees_all_deals(self, service):
        user = _user(UserRole.OWNER)
        service._repo.list_by_org = AsyncMock(return_value=([], 0))

        await service.list_deals(uuid4(), user)

        call_kwargs = service._repo.list_by_org.call_args.kwargs
        assert call_kwargs["assigned_to_id"] is None

    async def test_sales_rep_sees_only_assigned(self, service):
        user = _user(UserRole.SALES_REP)
        service._repo.list_by_org = AsyncMock(return_value=([], 0))

        await service.list_deals(uuid4(), user)

        call_kwargs = service._repo.list_by_org.call_args.kwargs
        assert call_kwargs["assigned_to_id"] == user.id

    async def test_pagination_metadata(self, service):
        user = _user(UserRole.OWNER)
        service._repo.list_by_org = AsyncMock(return_value=([], 0))

        result = await service.list_deals(uuid4(), user, page=2, page_size=5)

        assert result.page == 2
        assert result.page_size == 5


# ---------------------------------------------------------------------------
# get_deal
# ---------------------------------------------------------------------------


class TestGetDeal:
    async def test_returns_deal_when_found(self, service):
        deal = _deal()
        service._repo.get_by_id_and_org = AsyncMock(return_value=deal)

        result = await service.get_deal(deal.id, deal.organization_id)

        assert result is deal

    async def test_raises_not_found_when_missing(self, service):
        service._repo.get_by_id_and_org = AsyncMock(return_value=None)

        with pytest.raises(NotFoundError):
            await service.get_deal(uuid4(), uuid4())


# ---------------------------------------------------------------------------
# create_deal
# ---------------------------------------------------------------------------


class TestCreateDeal:
    async def test_owner_can_create_with_valid_stage(self, service):
        user = _user(UserRole.OWNER)
        org_id = uuid4()
        stage = _stage(org_id=org_id)
        new_deal = _deal(org_id=org_id, stage_id=stage.id)

        service._stage_repo.get_by_id_and_org = AsyncMock(return_value=stage)
        service._repo.create = AsyncMock(return_value=new_deal)

        payload = DealCreate(title="New Deal", stage_id=stage.id)
        result = await service.create_deal(payload, org_id, user)

        assert result is new_deal
        service._repo.create.assert_awaited_once()

    async def test_raises_not_found_when_stage_invalid(self, service):
        user = _user(UserRole.OWNER)
        service._stage_repo.get_by_id_and_org = AsyncMock(return_value=None)

        payload = DealCreate(title="New Deal", stage_id=uuid4())

        with pytest.raises(NotFoundError):
            await service.create_deal(payload, uuid4(), user)

    async def test_viewer_cannot_create(self, service):
        user = _user(UserRole.VIEWER)
        payload = DealCreate(title="New Deal", stage_id=uuid4())

        with pytest.raises(ForbiddenError):
            await service.create_deal(payload, uuid4(), user)

    async def test_currency_enum_is_serialized(self, service):
        user = _user(UserRole.OWNER)
        stage = _stage()
        service._stage_repo.get_by_id_and_org = AsyncMock(return_value=stage)
        service._repo.create = AsyncMock(return_value=_deal())

        payload = DealCreate(
            title="Deal", stage_id=stage.id, currency=DealCurrency.EUR, value=500.0
        )
        await service.create_deal(payload, uuid4(), user)

        create_kwargs = service._repo.create.call_args.kwargs
        assert create_kwargs["currency"] == "EUR"


# ---------------------------------------------------------------------------
# update_deal
# ---------------------------------------------------------------------------


class TestUpdateDeal:
    async def test_owner_can_update_any_deal(self, service):
        user = _user(UserRole.OWNER)
        deal = _deal(assigned_to_id=uuid4())
        service._repo.get_by_id_and_org = AsyncMock(return_value=deal)
        service._repo.update = AsyncMock(return_value=deal)
        payload = DealUpdate(title="Updated")

        result = await service.update_deal(deal.id, payload, deal.organization_id, user)

        assert result is deal

    async def test_sales_rep_can_update_assigned_deal(self, service):
        user = _user(UserRole.SALES_REP)
        deal = _deal(assigned_to_id=user.id)
        service._repo.get_by_id_and_org = AsyncMock(return_value=deal)
        service._repo.update = AsyncMock(return_value=deal)
        payload = DealUpdate(title="Updated")

        result = await service.update_deal(deal.id, payload, deal.organization_id, user)

        assert result is deal

    async def test_sales_rep_cannot_update_unassigned_deal(self, service):
        user = _user(UserRole.SALES_REP)
        deal = _deal(assigned_to_id=uuid4())
        service._repo.get_by_id_and_org = AsyncMock(return_value=deal)
        payload = DealUpdate(title="Updated")

        with pytest.raises(ForbiddenError):
            await service.update_deal(deal.id, payload, deal.organization_id, user)

    async def test_viewer_cannot_update(self, service):
        user = _user(UserRole.VIEWER)
        deal = _deal()
        service._repo.get_by_id_and_org = AsyncMock(return_value=deal)
        payload = DealUpdate(title="Updated")

        with pytest.raises(ForbiddenError):
            await service.update_deal(deal.id, payload, deal.organization_id, user)

    async def test_raises_not_found_when_deal_missing(self, service):
        user = _user(UserRole.OWNER)
        service._repo.get_by_id_and_org = AsyncMock(return_value=None)
        payload = DealUpdate(title="Updated")

        with pytest.raises(NotFoundError):
            await service.update_deal(uuid4(), payload, uuid4(), user)

    async def test_raises_not_found_when_new_stage_invalid(self, service):
        user = _user(UserRole.OWNER)
        deal = _deal()
        service._repo.get_by_id_and_org = AsyncMock(return_value=deal)
        service._stage_repo.get_by_id_and_org = AsyncMock(return_value=None)
        new_stage_id = uuid4()
        payload = DealUpdate(stage_id=new_stage_id)

        with pytest.raises(NotFoundError):
            await service.update_deal(deal.id, payload, deal.organization_id, user)

    async def test_moving_to_won_stage_sets_closed_at(self, service):
        """When a deal moves to a won stage and closed_at is None, it should be set."""
        user = _user(UserRole.OWNER)
        deal = _deal(closed_at=None)
        won_stage = _stage(is_won=True)

        service._repo.get_by_id_and_org = AsyncMock(return_value=deal)
        service._stage_repo.get_by_id_and_org = AsyncMock(return_value=won_stage)
        service._repo.update = AsyncMock(return_value=deal)

        payload = DealUpdate(stage_id=won_stage.id)
        await service.update_deal(deal.id, payload, deal.organization_id, user)

        update_kwargs = service._repo.update.call_args.kwargs
        assert "closed_at" in update_kwargs
        assert update_kwargs["closed_at"] is not None

    async def test_moving_to_lost_stage_sets_closed_at(self, service):
        """When a deal moves to a lost stage and closed_at is None, it should be set."""
        user = _user(UserRole.OWNER)
        deal = _deal(closed_at=None)
        lost_stage = _stage(is_lost=True)

        service._repo.get_by_id_and_org = AsyncMock(return_value=deal)
        service._stage_repo.get_by_id_and_org = AsyncMock(return_value=lost_stage)
        service._repo.update = AsyncMock(return_value=deal)

        payload = DealUpdate(stage_id=lost_stage.id)
        await service.update_deal(deal.id, payload, deal.organization_id, user)

        update_kwargs = service._repo.update.call_args.kwargs
        assert "closed_at" in update_kwargs

    async def test_already_closed_deal_does_not_overwrite_closed_at(self, service):
        """closed_at should NOT be overwritten if it is already set."""
        user = _user(UserRole.OWNER)
        original_close = datetime(2024, 6, 15)
        deal = _deal(closed_at=original_close)
        won_stage = _stage(is_won=True)

        service._repo.get_by_id_and_org = AsyncMock(return_value=deal)
        service._stage_repo.get_by_id_and_org = AsyncMock(return_value=won_stage)
        service._repo.update = AsyncMock(return_value=deal)

        payload = DealUpdate(stage_id=won_stage.id)
        await service.update_deal(deal.id, payload, deal.organization_id, user)

        update_kwargs = service._repo.update.call_args.kwargs
        assert "closed_at" not in update_kwargs

    async def test_empty_payload_returns_deal_unchanged(self, service):
        user = _user(UserRole.OWNER)
        deal = _deal()
        service._repo.get_by_id_and_org = AsyncMock(return_value=deal)
        service._repo.update = AsyncMock()
        payload = DealUpdate()

        result = await service.update_deal(deal.id, payload, deal.organization_id, user)

        assert result is deal
        service._repo.update.assert_not_awaited()


# ---------------------------------------------------------------------------
# move_stage
# ---------------------------------------------------------------------------


class TestMoveStage:
    async def test_move_stage_delegates_to_update_deal(self, service):
        """move_stage is a thin wrapper; ensure it calls update_deal with stage_id."""
        user = _user(UserRole.OWNER)
        deal = _deal()
        normal_stage = _stage()

        service._repo.get_by_id_and_org = AsyncMock(return_value=deal)
        service._stage_repo.get_by_id_and_org = AsyncMock(return_value=normal_stage)
        service._repo.update = AsyncMock(return_value=deal)

        payload = DealMoveStage(stage_id=normal_stage.id)
        result = await service.move_stage(deal.id, payload, deal.organization_id, user)

        assert result is deal
        service._repo.update.assert_awaited_once()


# ---------------------------------------------------------------------------
# delete_deal
# ---------------------------------------------------------------------------


class TestDeleteDeal:
    async def test_owner_can_delete(self, service):
        user = _user(UserRole.OWNER)
        deal = _deal()
        service._repo.get_by_id_and_org = AsyncMock(return_value=deal)
        service._repo.delete = AsyncMock()

        await service.delete_deal(deal.id, deal.organization_id, user)

        service._repo.delete.assert_awaited_once_with(deal)

    async def test_admin_can_delete(self, service):
        user = _user(UserRole.ADMIN)
        deal = _deal()
        service._repo.get_by_id_and_org = AsyncMock(return_value=deal)
        service._repo.delete = AsyncMock()

        await service.delete_deal(deal.id, deal.organization_id, user)

        service._repo.delete.assert_awaited_once()

    async def test_sales_rep_cannot_delete(self, service):
        user = _user(UserRole.SALES_REP)

        with pytest.raises(ForbiddenError):
            await service.delete_deal(uuid4(), uuid4(), user)

    async def test_viewer_cannot_delete(self, service):
        user = _user(UserRole.VIEWER)

        with pytest.raises(ForbiddenError):
            await service.delete_deal(uuid4(), uuid4(), user)

    async def test_raises_not_found_when_missing(self, service):
        user = _user(UserRole.OWNER)
        service._repo.get_by_id_and_org = AsyncMock(return_value=None)

        with pytest.raises(NotFoundError):
            await service.delete_deal(uuid4(), uuid4(), user)
