"""
Unit tests for PipelineStageService.

Mocks PipelineStageRepository at the instance level — no DB required.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.core.enums import UserRole
from src.core.exceptions import ForbiddenError, NotFoundError
from src.schemas.pipeline_stage import PipelineStageCreate, PipelineStageUpdate
from src.services.pipeline_stage import PipelineStageService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _user(role: str):
    return SimpleNamespace(id=uuid4(), organization_id=uuid4(), role=role)


def _stage(org_id=None, order=1):
    return SimpleNamespace(
        id=uuid4(),
        organization_id=org_id or uuid4(),
        name="Prospecting",
        order=order,
        is_won=False,
        is_lost=False,
    )


@pytest.fixture
def mock_session():
    return AsyncMock()


@pytest.fixture
def service(mock_session):
    svc = PipelineStageService(mock_session)
    svc._repo = MagicMock()
    return svc


# ---------------------------------------------------------------------------
# list_stages
# ---------------------------------------------------------------------------


class TestListStages:
    async def test_returns_ordered_stages(self, service):
        org_id = uuid4()
        stages = [_stage(org_id=org_id, order=i) for i in range(3)]
        service._repo.list_by_org_ordered = AsyncMock(return_value=stages)

        result = await service.list_stages(org_id)

        assert result == stages
        service._repo.list_by_org_ordered.assert_awaited_once_with(org_id)

    async def test_returns_empty_list_when_no_stages(self, service):
        service._repo.list_by_org_ordered = AsyncMock(return_value=[])

        result = await service.list_stages(uuid4())

        assert result == []


# ---------------------------------------------------------------------------
# create_stage
# ---------------------------------------------------------------------------


class TestCreateStage:
    async def test_owner_can_create(self, service):
        user = _user(UserRole.OWNER)
        org_id = uuid4()
        new_stage = _stage(org_id=org_id, order=2)
        service._repo.count_by_org = AsyncMock(return_value=2)
        service._repo.create = AsyncMock(return_value=new_stage)

        payload = PipelineStageCreate(name="Negotiation")
        result = await service.create_stage(payload, org_id, user)

        assert result is new_stage
        service._repo.create.assert_awaited_once()

    async def test_admin_can_create(self, service):
        user = _user(UserRole.ADMIN)
        service._repo.count_by_org = AsyncMock(return_value=0)
        service._repo.create = AsyncMock(return_value=_stage())

        await service.create_stage(PipelineStageCreate(name="New Stage"), uuid4(), user)

        service._repo.create.assert_awaited_once()

    async def test_sales_rep_cannot_create(self, service):
        user = _user(UserRole.SALES_REP)

        with pytest.raises(ForbiddenError):
            await service.create_stage(PipelineStageCreate(name="Stage"), uuid4(), user)

    async def test_viewer_cannot_create(self, service):
        user = _user(UserRole.VIEWER)

        with pytest.raises(ForbiddenError):
            await service.create_stage(PipelineStageCreate(name="Stage"), uuid4(), user)

    async def test_auto_order_when_order_is_zero(self, service):
        """When order=0 (default), the stage should be appended after existing stages."""
        user = _user(UserRole.OWNER)
        org_id = uuid4()
        service._repo.count_by_org = AsyncMock(return_value=3)
        service._repo.create = AsyncMock(return_value=_stage(order=3))

        payload = PipelineStageCreate(name="Closing", order=0)
        await service.create_stage(payload, org_id, user)

        create_kwargs = service._repo.create.call_args.kwargs
        assert create_kwargs["order"] == 3  # count value

    async def test_explicit_order_is_preserved(self, service):
        """When order > 0, the provided order should be used directly."""
        user = _user(UserRole.OWNER)
        service._repo.create = AsyncMock(return_value=_stage(order=5))

        payload = PipelineStageCreate(name="Stage", order=5)
        await service.create_stage(payload, uuid4(), user)

        create_kwargs = service._repo.create.call_args.kwargs
        assert create_kwargs["order"] == 5
        service._repo.count_by_org.assert_not_called()


# ---------------------------------------------------------------------------
# update_stage
# ---------------------------------------------------------------------------


class TestUpdateStage:
    async def test_owner_can_update(self, service):
        user = _user(UserRole.OWNER)
        stage = _stage()
        service._repo.get_by_id_and_org = AsyncMock(return_value=stage)
        service._repo.update = AsyncMock(return_value=stage)
        payload = PipelineStageUpdate(name="Updated Stage")

        result = await service.update_stage(stage.id, payload, stage.organization_id, user)

        assert result is stage

    async def test_admin_can_update(self, service):
        user = _user(UserRole.ADMIN)
        stage = _stage()
        service._repo.get_by_id_and_org = AsyncMock(return_value=stage)
        service._repo.update = AsyncMock(return_value=stage)

        await service.update_stage(
            stage.id, PipelineStageUpdate(name="Updated"), stage.organization_id, user
        )

        service._repo.update.assert_awaited_once()

    async def test_sales_rep_cannot_update(self, service):
        user = _user(UserRole.SALES_REP)

        with pytest.raises(ForbiddenError):
            await service.update_stage(uuid4(), PipelineStageUpdate(name="x"), uuid4(), user)

    async def test_viewer_cannot_update(self, service):
        user = _user(UserRole.VIEWER)

        with pytest.raises(ForbiddenError):
            await service.update_stage(uuid4(), PipelineStageUpdate(name="x"), uuid4(), user)

    async def test_raises_not_found_when_stage_missing(self, service):
        user = _user(UserRole.OWNER)
        service._repo.get_by_id_and_org = AsyncMock(return_value=None)

        with pytest.raises(NotFoundError):
            await service.update_stage(uuid4(), PipelineStageUpdate(name="x"), uuid4(), user)

    async def test_empty_payload_returns_stage_unchanged(self, service):
        user = _user(UserRole.OWNER)
        stage = _stage()
        service._repo.get_by_id_and_org = AsyncMock(return_value=stage)
        service._repo.update = AsyncMock()

        result = await service.update_stage(
            stage.id, PipelineStageUpdate(), stage.organization_id, user
        )

        assert result is stage
        service._repo.update.assert_not_awaited()


# ---------------------------------------------------------------------------
# delete_stage
# ---------------------------------------------------------------------------


class TestDeleteStage:
    async def test_owner_can_delete(self, service):
        user = _user(UserRole.OWNER)
        stage = _stage()
        service._repo.get_by_id_and_org = AsyncMock(return_value=stage)
        service._repo.delete = AsyncMock()

        await service.delete_stage(stage.id, stage.organization_id, user)

        service._repo.delete.assert_awaited_once_with(stage)

    async def test_admin_can_delete(self, service):
        user = _user(UserRole.ADMIN)
        stage = _stage()
        service._repo.get_by_id_and_org = AsyncMock(return_value=stage)
        service._repo.delete = AsyncMock()

        await service.delete_stage(stage.id, stage.organization_id, user)

        service._repo.delete.assert_awaited_once()

    async def test_sales_rep_cannot_delete(self, service):
        user = _user(UserRole.SALES_REP)

        with pytest.raises(ForbiddenError):
            await service.delete_stage(uuid4(), uuid4(), user)

    async def test_viewer_cannot_delete(self, service):
        user = _user(UserRole.VIEWER)

        with pytest.raises(ForbiddenError):
            await service.delete_stage(uuid4(), uuid4(), user)

    async def test_raises_not_found_when_missing(self, service):
        user = _user(UserRole.OWNER)
        service._repo.get_by_id_and_org = AsyncMock(return_value=None)

        with pytest.raises(NotFoundError):
            await service.delete_stage(uuid4(), uuid4(), user)
