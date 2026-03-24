"""
Unit tests for UserService.

Mocks UserRepository at the instance level — no DB required.
"""

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.core.enums import UserRole
from src.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from src.schemas.user import UserCreate, UserUpdate
from src.services.user import UserService

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_TEST_PASSWORD = "securePass1"  # noqa: S105 — intentionally plain in tests

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _user(role: str, user_id=None, org_id=None):
    return SimpleNamespace(
        id=user_id or uuid4(),
        organization_id=org_id or uuid4(),
        email="user@example.com",
        first_name="Alice",
        last_name="Smith",
        role=role,
        is_active=True,
        created_at=datetime(2024, 1, 1),
    )


@pytest.fixture
def mock_session():
    return AsyncMock()


@pytest.fixture
def service(mock_session):
    svc = UserService(mock_session)
    svc._repo = MagicMock()
    return svc


# ---------------------------------------------------------------------------
# list_users
# ---------------------------------------------------------------------------


class TestListUsers:
    async def test_returns_paginated_response(self, service):
        service._repo.list_by_org = AsyncMock(return_value=([], 0))

        result = await service.list_users(uuid4())

        assert result.total == 0

    async def test_pagination_offset_calculation(self, service):
        service._repo.list_by_org = AsyncMock(return_value=([], 0))

        await service.list_users(uuid4(), page=3, page_size=10)

        call_kwargs = service._repo.list_by_org.call_args.kwargs
        assert call_kwargs["offset"] == 20
        assert call_kwargs["limit"] == 10


# ---------------------------------------------------------------------------
# get_user
# ---------------------------------------------------------------------------


class TestGetUser:
    async def test_returns_user_when_found(self, service):
        user = _user(UserRole.SALES_REP)
        service._repo.get_by_id_and_org = AsyncMock(return_value=user)

        result = await service.get_user(user.id, user.organization_id)

        assert result is user

    async def test_raises_not_found_when_missing(self, service):
        service._repo.get_by_id_and_org = AsyncMock(return_value=None)

        with pytest.raises(NotFoundError):
            await service.get_user(uuid4(), uuid4())


# ---------------------------------------------------------------------------
# create_user
# ---------------------------------------------------------------------------


class TestCreateUser:
    async def test_owner_can_create_user(self, service):
        current_user = _user(UserRole.OWNER)
        new_user = _user(UserRole.SALES_REP)
        service._repo.get_by_email = AsyncMock(return_value=None)
        service._repo.create = AsyncMock(return_value=new_user)

        payload = UserCreate(
            email="new@example.com",
            password=_TEST_PASSWORD,
            first_name="Bob",
            last_name="Jones",
        )

        with patch("src.services.user.hash_password", return_value="hashed"):
            result = await service.create_user(payload, uuid4(), current_user)

        assert result is new_user

    async def test_admin_can_create_user(self, service):
        current_user = _user(UserRole.ADMIN)
        service._repo.get_by_email = AsyncMock(return_value=None)
        service._repo.create = AsyncMock(return_value=_user(UserRole.SALES_REP))

        payload = UserCreate(
            email="new@example.com",
            password=_TEST_PASSWORD,
            first_name="Bob",
            last_name="Jones",
        )

        with patch("src.services.user.hash_password", return_value="hashed"):
            await service.create_user(payload, uuid4(), current_user)

        service._repo.create.assert_awaited_once()

    async def test_sales_rep_cannot_create_user(self, service):
        current_user = _user(UserRole.SALES_REP)
        payload = UserCreate(
            email="new@example.com",
            password=_TEST_PASSWORD,
            first_name="Bob",
            last_name="Jones",
        )

        with pytest.raises(ForbiddenError):
            await service.create_user(payload, uuid4(), current_user)

    async def test_raises_conflict_when_email_exists(self, service):
        current_user = _user(UserRole.OWNER)
        existing = _user(UserRole.SALES_REP)
        service._repo.get_by_email = AsyncMock(return_value=existing)

        payload = UserCreate(
            email="existing@example.com",
            password=_TEST_PASSWORD,
            first_name="Bob",
            last_name="Jones",
        )

        with pytest.raises(ConflictError):
            await service.create_user(payload, uuid4(), current_user)


# ---------------------------------------------------------------------------
# update_user
# ---------------------------------------------------------------------------


class TestUpdateUser:
    async def test_owner_can_update_any_user(self, service):
        current_user = _user(UserRole.OWNER)
        target = _user(UserRole.SALES_REP)
        service._repo.get_by_id_and_org = AsyncMock(return_value=target)
        service._repo.update = AsyncMock(return_value=target)

        payload = UserUpdate(first_name="Updated")
        result = await service.update_user(target.id, payload, target.organization_id, current_user)

        assert result is target

    async def test_admin_can_update_non_owner(self, service):
        current_user = _user(UserRole.ADMIN)
        target = _user(UserRole.SALES_REP)
        service._repo.get_by_id_and_org = AsyncMock(return_value=target)
        service._repo.update = AsyncMock(return_value=target)

        payload = UserUpdate(first_name="Updated")
        result = await service.update_user(target.id, payload, target.organization_id, current_user)

        assert result is target

    async def test_admin_cannot_modify_owner(self, service):
        current_user = _user(UserRole.ADMIN)
        target = _user(UserRole.OWNER)
        service._repo.get_by_id_and_org = AsyncMock(return_value=target)

        payload = UserUpdate(first_name="Updated")

        with pytest.raises(ForbiddenError):
            await service.update_user(target.id, payload, target.organization_id, current_user)

    async def test_sales_rep_cannot_update_users(self, service):
        current_user = _user(UserRole.SALES_REP)
        payload = UserUpdate(first_name="Updated")

        with pytest.raises(ForbiddenError):
            await service.update_user(uuid4(), payload, uuid4(), current_user)

    async def test_raises_not_found_when_target_missing(self, service):
        current_user = _user(UserRole.OWNER)
        service._repo.get_by_id_and_org = AsyncMock(return_value=None)
        payload = UserUpdate(first_name="Updated")

        with pytest.raises(NotFoundError):
            await service.update_user(uuid4(), payload, uuid4(), current_user)

    async def test_role_enum_is_serialized(self, service):
        current_user = _user(UserRole.OWNER)
        target = _user(UserRole.SALES_REP)
        service._repo.get_by_id_and_org = AsyncMock(return_value=target)
        service._repo.update = AsyncMock(return_value=target)

        payload = UserUpdate(role=UserRole.ADMIN)
        await service.update_user(target.id, payload, target.organization_id, current_user)

        update_kwargs = service._repo.update.call_args.kwargs
        assert update_kwargs["role"] == "admin"


# ---------------------------------------------------------------------------
# delete_user (soft deactivation)
# ---------------------------------------------------------------------------


class TestDeleteUser:
    async def test_owner_can_deactivate_other_user(self, service):
        current_user = _user(UserRole.OWNER)
        target = _user(UserRole.SALES_REP)
        service._repo.get_by_id_and_org = AsyncMock(return_value=target)
        service._repo.update = AsyncMock(return_value=target)

        await service.delete_user(target.id, target.organization_id, current_user)

        service._repo.update.assert_awaited_once_with(target, is_active=False)

    async def test_admin_can_deactivate_sales_rep(self, service):
        current_user = _user(UserRole.ADMIN)
        target = _user(UserRole.SALES_REP)
        service._repo.get_by_id_and_org = AsyncMock(return_value=target)
        service._repo.update = AsyncMock(return_value=target)

        await service.delete_user(target.id, target.organization_id, current_user)

        service._repo.update.assert_awaited_once_with(target, is_active=False)

    async def test_admin_cannot_deactivate_owner(self, service):
        current_user = _user(UserRole.ADMIN)
        target = _user(UserRole.OWNER)
        service._repo.get_by_id_and_org = AsyncMock(return_value=target)

        with pytest.raises(ForbiddenError):
            await service.delete_user(target.id, target.organization_id, current_user)

    async def test_user_cannot_deactivate_themselves(self, service):
        shared_id = uuid4()
        current_user = _user(UserRole.OWNER, user_id=shared_id)
        target = _user(UserRole.OWNER, user_id=shared_id)
        service._repo.get_by_id_and_org = AsyncMock(return_value=target)

        with pytest.raises(ForbiddenError):
            await service.delete_user(target.id, target.organization_id, current_user)

    async def test_sales_rep_cannot_deactivate_users(self, service):
        current_user = _user(UserRole.SALES_REP)

        with pytest.raises(ForbiddenError):
            await service.delete_user(uuid4(), uuid4(), current_user)

    async def test_raises_not_found_when_target_missing(self, service):
        current_user = _user(UserRole.OWNER)
        service._repo.get_by_id_and_org = AsyncMock(return_value=None)

        with pytest.raises(NotFoundError):
            await service.delete_user(uuid4(), uuid4(), current_user)
