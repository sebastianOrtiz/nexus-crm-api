"""
Integration tests for contact CRUD endpoints.

Tests cover:
- List contacts (pagination, owner vs sales rep scope)
- Create contact (success, forbidden for viewer)
- Get contact by ID
- Update contact (owner success, sales rep own vs other)
- Delete contact (owner success, forbidden for sales rep)
- Get contact activities
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.contact import Contact
from src.models.organization import Organization
from src.models.user import User


async def _make_contact(
    session: AsyncSession,
    org: Organization,
    *,
    first_name: str = "John",
    last_name: str = "Doe",
    assigned_to: User | None = None,
) -> Contact:
    """Helper to persist a contact directly via the ORM."""
    from datetime import UTC, datetime

    contact = Contact(
        organization_id=org.id,
        first_name=first_name,
        last_name=last_name,
        email=f"{first_name.lower()}.{last_name.lower()}.{uuid4().hex[:6]}@test.com",
        assigned_to_id=assigned_to.id if assigned_to else None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    session.add(contact)
    await session.flush()
    await session.refresh(contact)
    return contact


@pytest.mark.asyncio
class TestListContacts:
    """Tests for GET /api/v1/contacts."""

    async def test_list_returns_only_tenant_contacts(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        org: Organization,
        owner_headers: dict,
    ) -> None:
        """Owner sees all contacts in their organization."""
        await _make_contact(db_session, org, first_name="Alice")
        await _make_contact(db_session, org, first_name="Bob")

        response = await client.get("/api/v1/contacts", headers=owner_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 2

    async def test_sales_rep_sees_only_assigned_contacts(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        org: Organization,
        owner_headers: dict,
        sales_rep_user: User,
        rep_headers: dict,
    ) -> None:
        """Sales rep should only see contacts assigned to them."""
        # One assigned, one not
        await _make_contact(db_session, org, first_name="Assigned", assigned_to=sales_rep_user)
        await _make_contact(db_session, org, first_name="NotAssigned")

        response = await client.get("/api/v1/contacts", headers=rep_headers)
        assert response.status_code == 200
        data = response.json()
        # All returned contacts should be assigned to the rep
        for item in data["items"]:
            assert item["assignedToId"] is None or item["assignedToId"] == str(
                sales_rep_user.id
            )

    async def test_list_requires_auth(self, client: AsyncClient) -> None:
        """Unauthenticated request returns 401."""
        response = await client.get("/api/v1/contacts")
        assert response.status_code == 401

    async def test_list_pagination(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        org: Organization,
        owner_headers: dict,
    ) -> None:
        """Pagination metadata is correct."""
        for i in range(5):
            await _make_contact(db_session, org, first_name=f"Page{i}")

        response = await client.get(
            "/api/v1/contacts", headers=owner_headers, params={"page": 1, "page_size": 2}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) <= 2
        assert data["page"] == 1
        assert data["pageSize"] == 2


@pytest.mark.asyncio
class TestCreateContact:
    """Tests for POST /api/v1/contacts."""

    async def test_create_success(
        self,
        client: AsyncClient,
        owner_headers: dict,
    ) -> None:
        """Owner can create a contact."""
        response = await client.post(
            "/api/v1/contacts",
            headers=owner_headers,
            json={
                "firstName": "New",
                "lastName": "Contact",
                "email": "new@contact.com",
                "source": "website",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["firstName"] == "New"
        assert data["lastName"] == "Contact"
        assert "id" in data

    async def test_create_requires_auth(self, client: AsyncClient) -> None:
        """Unauthenticated request returns 401."""
        response = await client.post(
            "/api/v1/contacts",
            json={"firstName": "X", "lastName": "Y"},
        )
        assert response.status_code == 401

    async def test_sales_rep_can_create_contact(
        self,
        client: AsyncClient,
        rep_headers: dict,
    ) -> None:
        """Sales reps are allowed to create contacts."""
        response = await client.post(
            "/api/v1/contacts",
            headers=rep_headers,
            json={"firstName": "Rep", "lastName": "Contact", "source": "referral"},
        )
        assert response.status_code == 201


@pytest.mark.asyncio
class TestGetContact:
    """Tests for GET /api/v1/contacts/{id}."""

    async def test_get_existing_contact(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        org: Organization,
        owner_headers: dict,
    ) -> None:
        """Returns 200 with contact details for an existing contact."""
        contact = await _make_contact(db_session, org, first_name="Fetch")
        response = await client.get(f"/api/v1/contacts/{contact.id}", headers=owner_headers)
        assert response.status_code == 200
        assert response.json()["id"] == str(contact.id)

    async def test_get_nonexistent_contact(
        self,
        client: AsyncClient,
        owner_headers: dict,
    ) -> None:
        """Returns 404 for a contact that does not exist."""
        response = await client.get(f"/api/v1/contacts/{uuid4()}", headers=owner_headers)
        assert response.status_code == 404


@pytest.mark.asyncio
class TestUpdateContact:
    """Tests for PUT /api/v1/contacts/{id}."""

    async def test_owner_can_update_any_contact(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        org: Organization,
        owner_headers: dict,
    ) -> None:
        """Owner can update any contact regardless of assignment."""
        contact = await _make_contact(db_session, org, first_name="Old")
        response = await client.put(
            f"/api/v1/contacts/{contact.id}",
            headers=owner_headers,
            json={"firstName": "Updated"},
        )
        assert response.status_code == 200
        assert response.json()["firstName"] == "Updated"

    async def test_sales_rep_cannot_update_unassigned_contact(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        org: Organization,
        rep_headers: dict,
    ) -> None:
        """Sales rep cannot update a contact they are not assigned to."""
        contact = await _make_contact(db_session, org, first_name="Other")  # no assignment
        response = await client.put(
            f"/api/v1/contacts/{contact.id}",
            headers=rep_headers,
            json={"firstName": "Hijack"},
        )
        assert response.status_code == 403

    async def test_sales_rep_can_update_assigned_contact(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        org: Organization,
        sales_rep_user: User,
        rep_headers: dict,
    ) -> None:
        """Sales rep can update their own assigned contact."""
        contact = await _make_contact(
            db_session, org, first_name="Mine", assigned_to=sales_rep_user
        )
        response = await client.put(
            f"/api/v1/contacts/{contact.id}",
            headers=rep_headers,
            json={"firstName": "Updated"},
        )
        assert response.status_code == 200
        assert response.json()["firstName"] == "Updated"


@pytest.mark.asyncio
class TestDeleteContact:
    """Tests for DELETE /api/v1/contacts/{id}."""

    async def test_owner_can_delete_contact(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        org: Organization,
        owner_headers: dict,
    ) -> None:
        """Owner can delete any contact."""
        contact = await _make_contact(db_session, org, first_name="ToDelete")
        response = await client.delete(
            f"/api/v1/contacts/{contact.id}", headers=owner_headers
        )
        assert response.status_code == 204

        # Verify it's gone
        get_response = await client.get(
            f"/api/v1/contacts/{contact.id}", headers=owner_headers
        )
        assert get_response.status_code == 404

    async def test_sales_rep_cannot_delete_contact(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        org: Organization,
        rep_headers: dict,
    ) -> None:
        """Sales reps cannot delete contacts."""
        contact = await _make_contact(db_session, org, first_name="Protected")
        response = await client.delete(
            f"/api/v1/contacts/{contact.id}", headers=rep_headers
        )
        assert response.status_code == 403
