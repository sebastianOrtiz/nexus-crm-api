"""
Unit tests for OrganizationService.

Mocks OrganizationRepository at the instance level — no DB required.
"""

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.core.enums import OrganizationPlan, UserRole
from src.core.exceptions import ForbiddenError, NotFoundError
from src.schemas.organization import OrganizationUpdate
from src.services.organization import OrganizationService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _user(role: str):
    return SimpleNamespace(id=uuid4(), organization_id=uuid4(), role=role)


def _org(org_id=None):
    return SimpleNamespace(
        id=org_id or uuid4(),
        name="Acme Inc",
        slug="acme-inc",
        plan="free",
        is_active=True,
        created_at=datetime(2024, 1, 1),
        updated_at=datetime(2024, 1, 1),
    )


@pytest.fixture
def mock_session():
    return AsyncMock()


@pytest.fixture
def service(mock_session):
    svc = OrganizationService(mock_session)
    svc._repo = MagicMock()
    return svc


# ---------------------------------------------------------------------------
# get
# ---------------------------------------------------------------------------


class TestGetOrganization:
    async def test_returns_org_when_found(self, service):
        org = _org()
        service._repo.get_by_id = AsyncMock(return_value=org)

        result = await service.get(org.id)

        assert result is org
        service._repo.get_by_id.assert_awaited_once_with(org.id)

    async def test_raises_not_found_when_missing(self, service):
        service._repo.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(NotFoundError):
            await service.get(uuid4())


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------


class TestUpdateOrganization:
    async def test_owner_can_update(self, service):
        user = _user(UserRole.OWNER)
        org = _org()
        service._repo.get_by_id = AsyncMock(return_value=org)
        service._repo.update = AsyncMock(return_value=org)
        payload = OrganizationUpdate(name="New Name")

        result = await service.update(org.id, payload, user)

        assert result is org
        service._repo.update.assert_awaited_once()

    async def test_admin_cannot_update(self, service):
        user = _user(UserRole.ADMIN)
        payload = OrganizationUpdate(name="New Name")

        with pytest.raises(ForbiddenError):
            await service.update(uuid4(), payload, user)

    async def test_sales_rep_cannot_update(self, service):
        user = _user(UserRole.SALES_REP)
        payload = OrganizationUpdate(name="New Name")

        with pytest.raises(ForbiddenError):
            await service.update(uuid4(), payload, user)

    async def test_viewer_cannot_update(self, service):
        user = _user(UserRole.VIEWER)
        payload = OrganizationUpdate(name="New Name")

        with pytest.raises(ForbiddenError):
            await service.update(uuid4(), payload, user)

    async def test_raises_not_found_when_org_missing(self, service):
        user = _user(UserRole.OWNER)
        service._repo.get_by_id = AsyncMock(return_value=None)
        payload = OrganizationUpdate(name="New Name")

        with pytest.raises(NotFoundError):
            await service.update(uuid4(), payload, user)

    async def test_empty_payload_returns_org_unchanged(self, service):
        """An update with no fields returns the org without calling repo.update."""
        user = _user(UserRole.OWNER)
        org = _org()
        service._repo.get_by_id = AsyncMock(return_value=org)
        service._repo.update = AsyncMock()
        payload = OrganizationUpdate()  # all None

        result = await service.update(org.id, payload, user)

        assert result is org
        service._repo.update.assert_not_awaited()

    async def test_plan_enum_field_is_accepted(self, service):
        user = _user(UserRole.OWNER)
        org = _org()
        service._repo.get_by_id = AsyncMock(return_value=org)
        service._repo.update = AsyncMock(return_value=org)
        payload = OrganizationUpdate(plan=OrganizationPlan.PROFESSIONAL)

        await service.update(org.id, payload, user)

        update_kwargs = service._repo.update.call_args.kwargs
        assert "plan" in update_kwargs
