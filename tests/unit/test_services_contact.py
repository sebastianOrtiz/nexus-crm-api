"""
Unit tests for ContactService.

Mocks ContactRepository and ActivityRepository at the instance level so no
database connection is required.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.core.enums import ContactSource, UserRole
from src.core.exceptions import ForbiddenError, NotFoundError
from src.schemas.contact import ContactCreate, ContactUpdate
from src.services.contact import ContactService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _user(role: str, user_id=None, org_id=None):
    return SimpleNamespace(
        id=user_id or uuid4(),
        organization_id=org_id or uuid4(),
        role=role,
    )


def _contact(org_id=None, assigned_to_id=None):
    return SimpleNamespace(
        id=uuid4(),
        organization_id=org_id or uuid4(),
        first_name="John",
        last_name="Doe",
        email="john@example.com",
        phone=None,
        position=None,
        source="other",
        notes=None,
        company_id=None,
        assigned_to_id=assigned_to_id,
        created_at=__import__("datetime").datetime(2024, 1, 1),
        updated_at=__import__("datetime").datetime(2024, 1, 1),
    )


@pytest.fixture
def mock_session():
    return AsyncMock()


@pytest.fixture
def service(mock_session):
    svc = ContactService(mock_session)
    # Replace repos with mocks so tests control return values
    svc._repo = MagicMock()
    svc._activity_repo = MagicMock()
    return svc


# ---------------------------------------------------------------------------
# list_contacts
# ---------------------------------------------------------------------------


class TestListContacts:
    async def test_owner_sees_all_contacts(self, service):
        """Owner should NOT filter by assigned_to_id."""
        org_id = uuid4()
        user = _user(UserRole.OWNER, org_id=org_id)
        service._repo.list_by_org = AsyncMock(return_value=([], 0))

        result = await service.list_contacts(org_id, user)

        call_kwargs = service._repo.list_by_org.call_args.kwargs
        assert call_kwargs["assigned_to_id"] is None
        assert result.total == 0

    async def test_sales_rep_sees_only_assigned(self, service):
        """Sales rep should filter by their own user ID."""
        org_id = uuid4()
        user = _user(UserRole.SALES_REP, org_id=org_id)
        service._repo.list_by_org = AsyncMock(return_value=([], 0))

        await service.list_contacts(org_id, user)

        call_kwargs = service._repo.list_by_org.call_args.kwargs
        assert call_kwargs["assigned_to_id"] == user.id

    async def test_admin_sees_all_contacts(self, service):
        """Admin should NOT be filtered by assigned_to_id."""
        org_id = uuid4()
        user = _user(UserRole.ADMIN)
        service._repo.list_by_org = AsyncMock(return_value=([], 0))

        await service.list_contacts(org_id, user)

        call_kwargs = service._repo.list_by_org.call_args.kwargs
        assert call_kwargs["assigned_to_id"] is None

    async def test_pagination_metadata(self, service):
        """Pages calculation should be correct for a non-empty result."""
        org_id = uuid4()
        user = _user(UserRole.OWNER)
        contact = _contact(org_id=org_id)
        # Simulate model_validate by giving the contact all required fields
        service._repo.list_by_org = AsyncMock(return_value=([contact], 1))

        # We need a real Contact-like object for model_validate; patch the schema call
        from unittest.mock import patch

        with patch("src.services.contact.ContactResponse.model_validate", return_value=MagicMock()):
            result = await service.list_contacts(org_id, user, page=1, page_size=20)

        assert result.total == 1
        assert result.page == 1


# ---------------------------------------------------------------------------
# get_contact
# ---------------------------------------------------------------------------


class TestGetContact:
    async def test_returns_contact_when_found(self, service):
        contact = _contact()
        service._repo.get_by_id_and_org = AsyncMock(return_value=contact)

        result = await service.get_contact(contact.id, contact.organization_id)

        assert result is contact

    async def test_raises_not_found_when_missing(self, service):
        service._repo.get_by_id_and_org = AsyncMock(return_value=None)

        with pytest.raises(NotFoundError):
            await service.get_contact(uuid4(), uuid4())


# ---------------------------------------------------------------------------
# create_contact
# ---------------------------------------------------------------------------


class TestCreateContact:
    async def test_owner_can_create(self, service):
        user = _user(UserRole.OWNER)
        org_id = uuid4()
        payload = ContactCreate(first_name="Jane", last_name="Doe")
        new_contact = _contact(org_id=org_id)
        service._repo.create = AsyncMock(return_value=new_contact)

        result = await service.create_contact(payload, org_id, user)

        assert result is new_contact
        service._repo.create.assert_awaited_once()

    async def test_sales_rep_can_create(self, service):
        user = _user(UserRole.SALES_REP)
        org_id = uuid4()
        payload = ContactCreate(first_name="Jane", last_name="Doe")
        service._repo.create = AsyncMock(return_value=_contact())

        await service.create_contact(payload, org_id, user)

        service._repo.create.assert_awaited_once()

    async def test_viewer_cannot_create(self, service):
        user = _user(UserRole.VIEWER)
        payload = ContactCreate(first_name="Jane", last_name="Doe")

        with pytest.raises(ForbiddenError):
            await service.create_contact(payload, uuid4(), user)

    async def test_source_enum_is_serialized_to_string(self, service):
        """The 'source' enum value should be stored as its string value."""
        user = _user(UserRole.OWNER)
        org_id = uuid4()
        payload = ContactCreate(
            first_name="Jane",
            last_name="Doe",
            source=ContactSource.REFERRAL,
        )
        service._repo.create = AsyncMock(return_value=_contact())

        await service.create_contact(payload, org_id, user)

        create_kwargs = service._repo.create.call_args.kwargs
        assert create_kwargs["source"] == "referral"


# ---------------------------------------------------------------------------
# update_contact
# ---------------------------------------------------------------------------


class TestUpdateContact:
    async def test_owner_can_update_any_contact(self, service):
        user = _user(UserRole.OWNER)
        contact = _contact(assigned_to_id=uuid4())  # assigned to someone else
        service._repo.get_by_id_and_org = AsyncMock(return_value=contact)
        service._repo.update = AsyncMock(return_value=contact)
        payload = ContactUpdate(first_name="Updated")

        result = await service.update_contact(contact.id, payload, contact.organization_id, user)

        assert result is contact

    async def test_sales_rep_can_update_assigned_contact(self, service):
        user = _user(UserRole.SALES_REP)
        contact = _contact(assigned_to_id=user.id)
        service._repo.get_by_id_and_org = AsyncMock(return_value=contact)
        service._repo.update = AsyncMock(return_value=contact)
        payload = ContactUpdate(first_name="Updated")

        result = await service.update_contact(contact.id, payload, contact.organization_id, user)

        assert result is contact

    async def test_sales_rep_cannot_update_unassigned_contact(self, service):
        user = _user(UserRole.SALES_REP)
        other_id = uuid4()
        contact = _contact(assigned_to_id=other_id)
        service._repo.get_by_id_and_org = AsyncMock(return_value=contact)
        payload = ContactUpdate(first_name="Updated")

        with pytest.raises(ForbiddenError):
            await service.update_contact(contact.id, payload, contact.organization_id, user)

    async def test_viewer_cannot_update(self, service):
        user = _user(UserRole.VIEWER)
        contact = _contact()
        service._repo.get_by_id_and_org = AsyncMock(return_value=contact)
        payload = ContactUpdate(first_name="Updated")

        with pytest.raises(ForbiddenError):
            await service.update_contact(contact.id, payload, contact.organization_id, user)

    async def test_raises_not_found_when_contact_missing(self, service):
        user = _user(UserRole.OWNER)
        service._repo.get_by_id_and_org = AsyncMock(return_value=None)
        payload = ContactUpdate(first_name="Updated")

        with pytest.raises(NotFoundError):
            await service.update_contact(uuid4(), payload, uuid4(), user)

    async def test_empty_payload_returns_contact_unchanged(self, service):
        """An update with no fields should return the contact without calling repo.update."""
        user = _user(UserRole.OWNER)
        contact = _contact()
        service._repo.get_by_id_and_org = AsyncMock(return_value=contact)
        service._repo.update = AsyncMock()
        payload = ContactUpdate()  # all fields None

        result = await service.update_contact(contact.id, payload, contact.organization_id, user)

        assert result is contact
        service._repo.update.assert_not_awaited()


# ---------------------------------------------------------------------------
# delete_contact
# ---------------------------------------------------------------------------


class TestDeleteContact:
    async def test_owner_can_delete(self, service):
        user = _user(UserRole.OWNER)
        contact = _contact()
        service._repo.get_by_id_and_org = AsyncMock(return_value=contact)
        service._repo.delete = AsyncMock()

        await service.delete_contact(contact.id, contact.organization_id, user)

        service._repo.delete.assert_awaited_once_with(contact)

    async def test_admin_can_delete(self, service):
        user = _user(UserRole.ADMIN)
        contact = _contact()
        service._repo.get_by_id_and_org = AsyncMock(return_value=contact)
        service._repo.delete = AsyncMock()

        await service.delete_contact(contact.id, contact.organization_id, user)

        service._repo.delete.assert_awaited_once()

    async def test_sales_rep_cannot_delete(self, service):
        user = _user(UserRole.SALES_REP)

        with pytest.raises(ForbiddenError):
            await service.delete_contact(uuid4(), uuid4(), user)

    async def test_viewer_cannot_delete(self, service):
        user = _user(UserRole.VIEWER)

        with pytest.raises(ForbiddenError):
            await service.delete_contact(uuid4(), uuid4(), user)

    async def test_raises_not_found_when_missing(self, service):
        user = _user(UserRole.OWNER)
        service._repo.get_by_id_and_org = AsyncMock(return_value=None)

        with pytest.raises(NotFoundError):
            await service.delete_contact(uuid4(), uuid4(), user)


# ---------------------------------------------------------------------------
# get_contact_activities
# ---------------------------------------------------------------------------


class TestGetContactActivities:
    async def test_raises_not_found_when_contact_missing(self, service):
        service._repo.get_by_id_and_org = AsyncMock(return_value=None)

        with pytest.raises(NotFoundError):
            await service.get_contact_activities(uuid4(), uuid4())

    async def test_returns_empty_list_when_no_activities(self, service):
        contact = _contact()
        service._repo.get_by_id_and_org = AsyncMock(return_value=contact)
        service._activity_repo.list_by_contact = AsyncMock(return_value=[])

        result = await service.get_contact_activities(contact.id, contact.organization_id)

        assert result == []
