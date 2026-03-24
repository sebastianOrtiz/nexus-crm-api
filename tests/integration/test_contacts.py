"""
Integration tests for contact CRUD endpoints.

All repository calls are mocked — no PostgreSQL required.

Tests cover:
- GET  /api/v1/contacts              (list, pagination)
- POST /api/v1/contacts              (success, forbidden for viewer)
- GET  /api/v1/contacts/{id}         (success, 404)
- PUT  /api/v1/contacts/{id}         (owner success, 404)
- DELETE /api/v1/contacts/{id}       (owner success, forbidden for rep)
- GET  /api/v1/contacts/{id}/activities
"""

import uuid
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient

from tests.integration.conftest import (
    make_activity,
    make_contact,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CONTACT_PAYLOAD = {
    "first_name": "John",
    "last_name": "Doe",
    "email": "john.doe@test.com",
    "source": "website",
}


# ---------------------------------------------------------------------------
# List contacts
# ---------------------------------------------------------------------------


class TestListContacts:
    """GET /api/v1/contacts"""

    @patch("src.api.v1.routers.contacts.ContactService")
    async def test_list_returns_200(
        self, mock_svc_cls: AsyncMock, client_owner: AsyncClient
    ) -> None:
        """Owner gets a paginated list of contacts."""
        contact = make_contact()
        mock_svc_cls.return_value.list_contacts = AsyncMock(return_value=_paginated([contact]))

        response = await client_owner.get("/api/v1/contacts")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1

    @patch("src.api.v1.routers.contacts.ContactService")
    async def test_list_empty(self, mock_svc_cls: AsyncMock, client_owner: AsyncClient) -> None:
        """Empty tenant returns empty items list."""
        mock_svc_cls.return_value.list_contacts = AsyncMock(return_value=_paginated([]))

        response = await client_owner.get("/api/v1/contacts")

        assert response.status_code == 200
        assert response.json()["total"] == 0

    async def test_list_unauthenticated(self, client_no_auth: AsyncClient) -> None:
        """Unauthenticated request returns 401."""
        response = await client_no_auth.get("/api/v1/contacts")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Create contact
# ---------------------------------------------------------------------------


class TestCreateContact:
    """POST /api/v1/contacts"""

    @patch("src.api.v1.routers.contacts.ContactService")
    async def test_create_success_owner(
        self, mock_svc_cls: AsyncMock, client_owner: AsyncClient
    ) -> None:
        """Owner can create a contact — returns 201."""
        contact = make_contact()
        mock_svc_cls.return_value.create_contact = AsyncMock(return_value=contact)

        response = await client_owner.post("/api/v1/contacts", json=_CONTACT_PAYLOAD)

        assert response.status_code == 201
        data = response.json()
        assert data["firstName"] == contact.first_name
        assert data["lastName"] == contact.last_name

    @patch("src.api.v1.routers.contacts.ContactService")
    async def test_create_success_admin(
        self, mock_svc_cls: AsyncMock, client_admin: AsyncClient
    ) -> None:
        """Admin can create a contact."""
        contact = make_contact()
        mock_svc_cls.return_value.create_contact = AsyncMock(return_value=contact)

        response = await client_admin.post("/api/v1/contacts", json=_CONTACT_PAYLOAD)

        assert response.status_code == 201

    @patch("src.api.v1.routers.contacts.ContactService")
    async def test_create_forbidden_viewer(
        self, mock_svc_cls: AsyncMock, client_viewer: AsyncClient
    ) -> None:
        """Viewer cannot create contacts — service raises ForbiddenError → 403."""
        from src.core.exceptions import ForbiddenError

        mock_svc_cls.return_value.create_contact = AsyncMock(
            side_effect=ForbiddenError("Viewers cannot create contacts")
        )

        response = await client_viewer.post("/api/v1/contacts", json=_CONTACT_PAYLOAD)

        assert response.status_code == 403

    async def test_create_missing_required_fields(self, client_owner: AsyncClient) -> None:
        """Missing required fields return 422."""
        response = await client_owner.post("/api/v1/contacts", json={})
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Get contact
# ---------------------------------------------------------------------------


class TestGetContact:
    """GET /api/v1/contacts/{contact_id}"""

    @patch("src.api.v1.routers.contacts.ContactService")
    async def test_get_success(self, mock_svc_cls: AsyncMock, client_owner: AsyncClient) -> None:
        """Returns 200 with the contact data."""
        contact_id = uuid.uuid4()
        contact = make_contact(contact_id=contact_id)
        mock_svc_cls.return_value.get_contact = AsyncMock(return_value=contact)

        response = await client_owner.get(f"/api/v1/contacts/{contact_id}")

        assert response.status_code == 200
        assert response.json()["id"] == str(contact_id)

    @patch("src.api.v1.routers.contacts.ContactService")
    async def test_get_not_found(self, mock_svc_cls: AsyncMock, client_owner: AsyncClient) -> None:
        """Non-existent contact returns 404."""
        from src.core.exceptions import NotFoundError

        contact_id = uuid.uuid4()
        mock_svc_cls.return_value.get_contact = AsyncMock(
            side_effect=NotFoundError("Contact", str(contact_id))
        )

        response = await client_owner.get(f"/api/v1/contacts/{contact_id}")

        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Update contact
# ---------------------------------------------------------------------------


class TestUpdateContact:
    """PUT /api/v1/contacts/{contact_id}"""

    @patch("src.api.v1.routers.contacts.ContactService")
    async def test_update_success(self, mock_svc_cls: AsyncMock, client_owner: AsyncClient) -> None:
        """Owner can update a contact — returns 200 with updated data."""
        contact_id = uuid.uuid4()
        updated_contact = make_contact(contact_id=contact_id, first_name="Jane")
        mock_svc_cls.return_value.update_contact = AsyncMock(return_value=updated_contact)

        response = await client_owner.put(
            f"/api/v1/contacts/{contact_id}",
            json={"first_name": "Jane"},
        )

        assert response.status_code == 200
        assert response.json()["firstName"] == "Jane"

    @patch("src.api.v1.routers.contacts.ContactService")
    async def test_update_not_found(
        self, mock_svc_cls: AsyncMock, client_owner: AsyncClient
    ) -> None:
        """Updating a non-existent contact returns 404."""
        from src.core.exceptions import NotFoundError

        contact_id = uuid.uuid4()
        mock_svc_cls.return_value.update_contact = AsyncMock(
            side_effect=NotFoundError("Contact", str(contact_id))
        )

        response = await client_owner.put(
            f"/api/v1/contacts/{contact_id}", json={"first_name": "Jane"}
        )

        assert response.status_code == 404

    @patch("src.api.v1.routers.contacts.ContactService")
    async def test_update_forbidden_sales_rep(
        self, mock_svc_cls: AsyncMock, client_rep: AsyncClient
    ) -> None:
        """Sales rep cannot update a contact they are not assigned to — 403."""
        from src.core.exceptions import ForbiddenError

        contact_id = uuid.uuid4()
        mock_svc_cls.return_value.update_contact = AsyncMock(
            side_effect=ForbiddenError("Sales reps can only modify their assigned contacts")
        )

        response = await client_rep.put(
            f"/api/v1/contacts/{contact_id}", json={"first_name": "Jane"}
        )

        assert response.status_code == 403


# ---------------------------------------------------------------------------
# Delete contact
# ---------------------------------------------------------------------------


class TestDeleteContact:
    """DELETE /api/v1/contacts/{contact_id}"""

    @patch("src.api.v1.routers.contacts.ContactService")
    async def test_delete_success(self, mock_svc_cls: AsyncMock, client_owner: AsyncClient) -> None:
        """Owner can delete a contact — returns 204."""
        contact_id = uuid.uuid4()
        mock_svc_cls.return_value.delete_contact = AsyncMock(return_value=None)

        response = await client_owner.delete(f"/api/v1/contacts/{contact_id}")

        assert response.status_code == 204

    @patch("src.api.v1.routers.contacts.ContactService")
    async def test_delete_forbidden_for_rep(
        self, mock_svc_cls: AsyncMock, client_rep: AsyncClient
    ) -> None:
        """Sales rep cannot delete a contact — 403."""
        from src.core.exceptions import ForbiddenError

        contact_id = uuid.uuid4()
        mock_svc_cls.return_value.delete_contact = AsyncMock(
            side_effect=ForbiddenError("Only owners and admins can delete contacts")
        )

        response = await client_rep.delete(f"/api/v1/contacts/{contact_id}")

        assert response.status_code == 403

    @patch("src.api.v1.routers.contacts.ContactService")
    async def test_delete_not_found(
        self, mock_svc_cls: AsyncMock, client_owner: AsyncClient
    ) -> None:
        """Deleting a non-existent contact returns 404."""
        from src.core.exceptions import NotFoundError

        contact_id = uuid.uuid4()
        mock_svc_cls.return_value.delete_contact = AsyncMock(
            side_effect=NotFoundError("Contact", str(contact_id))
        )

        response = await client_owner.delete(f"/api/v1/contacts/{contact_id}")

        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Contact activities sub-resource
# ---------------------------------------------------------------------------


class TestContactActivities:
    """GET /api/v1/contacts/{contact_id}/activities"""

    @patch("src.api.v1.routers.contacts.ContactService")
    async def test_list_activities_success(
        self, mock_svc_cls: AsyncMock, client_owner: AsyncClient
    ) -> None:
        """Returns the list of activities for an existing contact."""
        from src.schemas.activity import ActivityResponse

        contact_id = uuid.uuid4()
        activity = make_activity()
        activity_response = ActivityResponse.model_validate(activity)
        mock_svc_cls.return_value.get_contact_activities = AsyncMock(
            return_value=[activity_response]
        )

        response = await client_owner.get(f"/api/v1/contacts/{contact_id}/activities")

        assert response.status_code == 200
        assert isinstance(response.json(), list)
        assert len(response.json()) == 1

    @patch("src.api.v1.routers.contacts.ContactService")
    async def test_list_activities_contact_not_found(
        self, mock_svc_cls: AsyncMock, client_owner: AsyncClient
    ) -> None:
        """Returns 404 when the contact does not exist."""
        from src.core.exceptions import NotFoundError

        contact_id = uuid.uuid4()
        mock_svc_cls.return_value.get_contact_activities = AsyncMock(
            side_effect=NotFoundError("Contact", str(contact_id))
        )

        response = await client_owner.get(f"/api/v1/contacts/{contact_id}/activities")

        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------


def _paginated(items: list) -> object:
    """Build a minimal PaginatedResponse-like object."""
    from types import SimpleNamespace

    from src.schemas.contact import ContactResponse

    validated = [ContactResponse.model_validate(i) for i in items]
    return SimpleNamespace(
        items=validated,
        total=len(items),
        page=1,
        page_size=20,
        pages=1,
    )
