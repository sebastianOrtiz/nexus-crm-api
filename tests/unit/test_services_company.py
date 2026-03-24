"""
Unit tests for CompanyService.

Mocks CompanyRepository and ContactRepository at the instance level.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.core.enums import UserRole
from src.core.exceptions import ForbiddenError, NotFoundError
from src.schemas.company import CompanyCreate, CompanyUpdate
from src.services.company import CompanyService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _user(role: str):
    return SimpleNamespace(id=uuid4(), organization_id=uuid4(), role=role)


def _company(org_id=None):
    return SimpleNamespace(
        id=uuid4(),
        organization_id=org_id or uuid4(),
        name="Acme Corp",
        domain="acme.com",
        industry=None,
        website=None,
        phone=None,
        address=None,
        notes=None,
        created_at=__import__("datetime").datetime(2024, 1, 1),
        updated_at=__import__("datetime").datetime(2024, 1, 1),
    )


@pytest.fixture
def mock_session():
    return AsyncMock()


@pytest.fixture
def service(mock_session):
    svc = CompanyService(mock_session)
    svc._repo = MagicMock()
    svc._contact_repo = MagicMock()
    return svc


# ---------------------------------------------------------------------------
# list_companies
# ---------------------------------------------------------------------------


class TestListCompanies:
    async def test_returns_paginated_response(self, service):
        service._repo.list_by_org = AsyncMock(return_value=([], 0))

        result = await service.list_companies(uuid4())

        assert result.total == 0
        assert result.page == 1

    async def test_pagination_uses_correct_offset(self, service):
        service._repo.list_by_org = AsyncMock(return_value=([], 0))

        await service.list_companies(uuid4(), page=3, page_size=10)

        call_kwargs = service._repo.list_by_org.call_args.kwargs
        assert call_kwargs["offset"] == 20  # (3-1) * 10
        assert call_kwargs["limit"] == 10


# ---------------------------------------------------------------------------
# get_company
# ---------------------------------------------------------------------------


class TestGetCompany:
    async def test_returns_company_when_found(self, service):
        company = _company()
        service._repo.get_by_id_and_org = AsyncMock(return_value=company)

        result = await service.get_company(company.id, company.organization_id)

        assert result is company

    async def test_raises_not_found_when_missing(self, service):
        service._repo.get_by_id_and_org = AsyncMock(return_value=None)

        with pytest.raises(NotFoundError):
            await service.get_company(uuid4(), uuid4())


# ---------------------------------------------------------------------------
# create_company
# ---------------------------------------------------------------------------


class TestCreateCompany:
    async def test_owner_can_create(self, service):
        user = _user(UserRole.OWNER)
        company = _company()
        service._repo.create = AsyncMock(return_value=company)
        payload = CompanyCreate(name="New Corp")

        result = await service.create_company(payload, uuid4(), user)

        assert result is company
        service._repo.create.assert_awaited_once()

    async def test_admin_can_create(self, service):
        user = _user(UserRole.ADMIN)
        service._repo.create = AsyncMock(return_value=_company())
        payload = CompanyCreate(name="New Corp")

        await service.create_company(payload, uuid4(), user)

        service._repo.create.assert_awaited_once()

    async def test_sales_rep_can_create(self, service):
        user = _user(UserRole.SALES_REP)
        service._repo.create = AsyncMock(return_value=_company())
        payload = CompanyCreate(name="New Corp")

        await service.create_company(payload, uuid4(), user)

        service._repo.create.assert_awaited_once()

    async def test_viewer_cannot_create(self, service):
        user = _user(UserRole.VIEWER)
        payload = CompanyCreate(name="New Corp")

        with pytest.raises(ForbiddenError):
            await service.create_company(payload, uuid4(), user)


# ---------------------------------------------------------------------------
# update_company
# ---------------------------------------------------------------------------


class TestUpdateCompany:
    async def test_owner_can_update(self, service):
        user = _user(UserRole.OWNER)
        company = _company()
        service._repo.get_by_id_and_org = AsyncMock(return_value=company)
        service._repo.update = AsyncMock(return_value=company)
        payload = CompanyUpdate(name="Updated Corp")

        result = await service.update_company(company.id, payload, company.organization_id, user)

        assert result is company

    async def test_viewer_cannot_update(self, service):
        user = _user(UserRole.VIEWER)
        payload = CompanyUpdate(name="Updated Corp")

        with pytest.raises(ForbiddenError):
            await service.update_company(uuid4(), payload, uuid4(), user)

    async def test_raises_not_found_when_missing(self, service):
        user = _user(UserRole.OWNER)
        service._repo.get_by_id_and_org = AsyncMock(return_value=None)
        payload = CompanyUpdate(name="Updated Corp")

        with pytest.raises(NotFoundError):
            await service.update_company(uuid4(), payload, uuid4(), user)

    async def test_empty_payload_returns_company_unchanged(self, service):
        user = _user(UserRole.ADMIN)
        company = _company()
        service._repo.get_by_id_and_org = AsyncMock(return_value=company)
        service._repo.update = AsyncMock()
        payload = CompanyUpdate()  # all fields None

        result = await service.update_company(company.id, payload, company.organization_id, user)

        assert result is company
        service._repo.update.assert_not_awaited()


# ---------------------------------------------------------------------------
# delete_company
# ---------------------------------------------------------------------------


class TestDeleteCompany:
    async def test_owner_can_delete(self, service):
        user = _user(UserRole.OWNER)
        company = _company()
        service._repo.get_by_id_and_org = AsyncMock(return_value=company)
        service._repo.delete = AsyncMock()

        await service.delete_company(company.id, company.organization_id, user)

        service._repo.delete.assert_awaited_once_with(company)

    async def test_admin_can_delete(self, service):
        user = _user(UserRole.ADMIN)
        company = _company()
        service._repo.get_by_id_and_org = AsyncMock(return_value=company)
        service._repo.delete = AsyncMock()

        await service.delete_company(company.id, company.organization_id, user)

        service._repo.delete.assert_awaited_once()

    async def test_sales_rep_cannot_delete(self, service):
        user = _user(UserRole.SALES_REP)

        with pytest.raises(ForbiddenError):
            await service.delete_company(uuid4(), uuid4(), user)

    async def test_viewer_cannot_delete(self, service):
        user = _user(UserRole.VIEWER)

        with pytest.raises(ForbiddenError):
            await service.delete_company(uuid4(), uuid4(), user)

    async def test_raises_not_found_when_missing(self, service):
        user = _user(UserRole.OWNER)
        service._repo.get_by_id_and_org = AsyncMock(return_value=None)

        with pytest.raises(NotFoundError):
            await service.delete_company(uuid4(), uuid4(), user)


# ---------------------------------------------------------------------------
# get_company_contacts
# ---------------------------------------------------------------------------


class TestGetCompanyContacts:
    async def test_raises_not_found_when_company_missing(self, service):
        service._repo.get_by_id_and_org = AsyncMock(return_value=None)

        with pytest.raises(NotFoundError):
            await service.get_company_contacts(uuid4(), uuid4())

    async def test_returns_empty_list_when_no_contacts(self, service):
        company = _company()
        service._repo.get_by_id_and_org = AsyncMock(return_value=company)
        service._contact_repo.list_by_company = AsyncMock(return_value=[])

        result = await service.get_company_contacts(company.id, company.organization_id)

        assert result == []
