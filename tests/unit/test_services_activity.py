"""
Unit tests for ActivityService.

Mocks ActivityRepository at the instance level — no DB required.
"""

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.core.enums import ActivityType, UserRole
from src.core.exceptions import ForbiddenError, NotFoundError
from src.schemas.activity import ActivityCreate, ActivityUpdate
from src.services.activity import ActivityService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _user(role: str, user_id=None):
    return SimpleNamespace(id=user_id or uuid4(), organization_id=uuid4(), role=role)


def _activity(org_id=None, user_id=None):
    return SimpleNamespace(
        id=uuid4(),
        organization_id=org_id or uuid4(),
        type="call",
        subject="Follow-up call",
        description=None,
        contact_id=None,
        deal_id=None,
        user_id=user_id or uuid4(),
        scheduled_at=None,
        completed_at=None,
        created_at=datetime(2024, 1, 1),
    )


@pytest.fixture
def mock_session():
    return AsyncMock()


@pytest.fixture
def service(mock_session):
    svc = ActivityService(mock_session)
    svc._repo = MagicMock()
    return svc


# ---------------------------------------------------------------------------
# list_activities
# ---------------------------------------------------------------------------


class TestListActivities:
    async def test_owner_sees_all_activities(self, service):
        user = _user(UserRole.OWNER)
        service._repo.list_by_org = AsyncMock(return_value=([], 0))

        await service.list_activities(uuid4(), user)

        call_kwargs = service._repo.list_by_org.call_args.kwargs
        assert call_kwargs["user_id"] is None

    async def test_sales_rep_sees_only_own_activities(self, service):
        user = _user(UserRole.SALES_REP)
        service._repo.list_by_org = AsyncMock(return_value=([], 0))

        await service.list_activities(uuid4(), user)

        call_kwargs = service._repo.list_by_org.call_args.kwargs
        assert call_kwargs["user_id"] == user.id

    async def test_activity_type_filter_is_forwarded(self, service):
        user = _user(UserRole.OWNER)
        service._repo.list_by_org = AsyncMock(return_value=([], 0))

        await service.list_activities(uuid4(), user, activity_type=ActivityType.CALL)

        call_kwargs = service._repo.list_by_org.call_args.kwargs
        assert call_kwargs["activity_type"] == ActivityType.CALL

    async def test_returns_paginated_response(self, service):
        user = _user(UserRole.ADMIN)
        service._repo.list_by_org = AsyncMock(return_value=([], 0))

        result = await service.list_activities(uuid4(), user, page=2, page_size=5)

        assert result.page == 2
        assert result.total == 0


# ---------------------------------------------------------------------------
# get_activity
# ---------------------------------------------------------------------------


class TestGetActivity:
    async def test_returns_activity_when_found(self, service):
        activity = _activity()
        service._repo.get_by_id_and_org = AsyncMock(return_value=activity)

        result = await service.get_activity(activity.id, activity.organization_id)

        assert result is activity

    async def test_raises_not_found_when_missing(self, service):
        service._repo.get_by_id_and_org = AsyncMock(return_value=None)

        with pytest.raises(NotFoundError):
            await service.get_activity(uuid4(), uuid4())


# ---------------------------------------------------------------------------
# create_activity
# ---------------------------------------------------------------------------


class TestCreateActivity:
    async def test_owner_can_create(self, service):
        user = _user(UserRole.OWNER)
        org_id = uuid4()
        activity = _activity(org_id=org_id, user_id=user.id)
        service._repo.create = AsyncMock(return_value=activity)
        payload = ActivityCreate(type=ActivityType.CALL, subject="Intro call")

        result = await service.create_activity(payload, org_id, user)

        assert result is activity
        service._repo.create.assert_awaited_once()

    async def test_sales_rep_can_create(self, service):
        user = _user(UserRole.SALES_REP)
        service._repo.create = AsyncMock(return_value=_activity())
        payload = ActivityCreate(type=ActivityType.EMAIL, subject="Follow-up email")

        await service.create_activity(payload, uuid4(), user)

        service._repo.create.assert_awaited_once()

    async def test_viewer_cannot_create(self, service):
        user = _user(UserRole.VIEWER)
        payload = ActivityCreate(type=ActivityType.NOTE, subject="A note")

        with pytest.raises(ForbiddenError):
            await service.create_activity(payload, uuid4(), user)

    async def test_type_enum_is_serialized_to_string(self, service):
        user = _user(UserRole.OWNER)
        service._repo.create = AsyncMock(return_value=_activity())
        payload = ActivityCreate(type=ActivityType.MEETING, subject="Kick-off meeting")

        await service.create_activity(payload, uuid4(), user)

        create_kwargs = service._repo.create.call_args.kwargs
        assert create_kwargs["type"] == "meeting"

    async def test_user_id_is_set_from_current_user(self, service):
        user = _user(UserRole.OWNER)
        service._repo.create = AsyncMock(return_value=_activity())
        payload = ActivityCreate(type=ActivityType.CALL, subject="Call")

        await service.create_activity(payload, uuid4(), user)

        create_kwargs = service._repo.create.call_args.kwargs
        assert create_kwargs["user_id"] == user.id


# ---------------------------------------------------------------------------
# update_activity
# ---------------------------------------------------------------------------


class TestUpdateActivity:
    async def test_owner_can_update_any_activity(self, service):
        user = _user(UserRole.OWNER)
        activity = _activity(user_id=uuid4())  # owned by someone else
        service._repo.get_by_id_and_org = AsyncMock(return_value=activity)
        service._repo.update = AsyncMock(return_value=activity)
        payload = ActivityUpdate(subject="Updated subject")

        result = await service.update_activity(activity.id, payload, activity.organization_id, user)

        assert result is activity

    async def test_sales_rep_can_update_own_activity(self, service):
        user = _user(UserRole.SALES_REP)
        activity = _activity(user_id=user.id)
        service._repo.get_by_id_and_org = AsyncMock(return_value=activity)
        service._repo.update = AsyncMock(return_value=activity)
        payload = ActivityUpdate(subject="Updated subject")

        result = await service.update_activity(activity.id, payload, activity.organization_id, user)

        assert result is activity

    async def test_sales_rep_cannot_update_others_activity(self, service):
        user = _user(UserRole.SALES_REP)
        activity = _activity(user_id=uuid4())  # owned by different user
        service._repo.get_by_id_and_org = AsyncMock(return_value=activity)
        payload = ActivityUpdate(subject="Updated subject")

        with pytest.raises(ForbiddenError):
            await service.update_activity(activity.id, payload, activity.organization_id, user)

    async def test_viewer_cannot_update(self, service):
        user = _user(UserRole.VIEWER)
        activity = _activity()
        service._repo.get_by_id_and_org = AsyncMock(return_value=activity)
        payload = ActivityUpdate(subject="Updated")

        with pytest.raises(ForbiddenError):
            await service.update_activity(activity.id, payload, activity.organization_id, user)

    async def test_raises_not_found_when_missing(self, service):
        user = _user(UserRole.OWNER)
        service._repo.get_by_id_and_org = AsyncMock(return_value=None)
        payload = ActivityUpdate(subject="Updated")

        with pytest.raises(NotFoundError):
            await service.update_activity(uuid4(), payload, uuid4(), user)

    async def test_type_enum_is_serialized_on_update(self, service):
        user = _user(UserRole.OWNER)
        activity = _activity(user_id=user.id)
        service._repo.get_by_id_and_org = AsyncMock(return_value=activity)
        service._repo.update = AsyncMock(return_value=activity)
        payload = ActivityUpdate(type=ActivityType.EMAIL)

        await service.update_activity(activity.id, payload, activity.organization_id, user)

        update_kwargs = service._repo.update.call_args.kwargs
        assert update_kwargs["type"] == "email"

    async def test_empty_payload_returns_activity_unchanged(self, service):
        user = _user(UserRole.OWNER)
        activity = _activity()
        service._repo.get_by_id_and_org = AsyncMock(return_value=activity)
        service._repo.update = AsyncMock()
        payload = ActivityUpdate()

        result = await service.update_activity(activity.id, payload, activity.organization_id, user)

        assert result is activity
        service._repo.update.assert_not_awaited()


# ---------------------------------------------------------------------------
# delete_activity
# ---------------------------------------------------------------------------


class TestDeleteActivity:
    async def test_owner_can_delete_any_activity(self, service):
        user = _user(UserRole.OWNER)
        activity = _activity(user_id=uuid4())
        service._repo.get_by_id_and_org = AsyncMock(return_value=activity)
        service._repo.delete = AsyncMock()

        await service.delete_activity(activity.id, activity.organization_id, user)

        service._repo.delete.assert_awaited_once_with(activity)

    async def test_sales_rep_can_delete_own_activity(self, service):
        user = _user(UserRole.SALES_REP)
        activity = _activity(user_id=user.id)
        service._repo.get_by_id_and_org = AsyncMock(return_value=activity)
        service._repo.delete = AsyncMock()

        await service.delete_activity(activity.id, activity.organization_id, user)

        service._repo.delete.assert_awaited_once()

    async def test_sales_rep_cannot_delete_others_activity(self, service):
        user = _user(UserRole.SALES_REP)
        activity = _activity(user_id=uuid4())
        service._repo.get_by_id_and_org = AsyncMock(return_value=activity)

        with pytest.raises(ForbiddenError):
            await service.delete_activity(activity.id, activity.organization_id, user)

    async def test_viewer_cannot_delete(self, service):
        user = _user(UserRole.VIEWER)
        activity = _activity()
        service._repo.get_by_id_and_org = AsyncMock(return_value=activity)

        with pytest.raises(ForbiddenError):
            await service.delete_activity(activity.id, activity.organization_id, user)

    async def test_raises_not_found_when_missing(self, service):
        user = _user(UserRole.OWNER)
        service._repo.get_by_id_and_org = AsyncMock(return_value=None)

        with pytest.raises(NotFoundError):
            await service.delete_activity(uuid4(), uuid4(), user)
