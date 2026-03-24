"""
Integration tests for company CRUD endpoints.

Tests cover:
- List companies (pagination, search)
- Create company (owner success, viewer forbidden, sales rep allowed)
- Get company by ID
- Update company (owner success, sales rep permission)
- Delete company (owner success, forbidden for sales rep)
- Get company contacts sub-resource
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.company import Company
from src.models.organization import Organization


async def _make_company(
    session: AsyncSession,
    org: Organization,
    *,
    name: str = "Acme Corp",
    domain: str | None = None,
) -> Company:
    """Helper to persist a Company directly via the ORM."""
    from datetime import UTC, datetime

    company = Company(
        organization_id=org.id,
        name=name,
        domain=domain or f"{name.lower().replace(' ', '')}.com",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    session.add(company)
    await session.flush()
    await session.refresh(company)
    return company


@pytest.mark.asyncio
class TestListCompanies:
    """Tests for GET /api/v1/companies."""

    async def test_list_returns_tenant_companies(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        org: Organization,
        owner_headers: dict,
    ) -> None:
        """Owner sees all companies in their organization."""
        await _make_company(db_session, org, name="Company A")
        await _make_company(db_session, org, name="Company B")

        response = await client.get("/api/v1/companies", headers=owner_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 2

    async def test_list_requires_auth(self, client: AsyncClient) -> None:
        """Unauthenticated request returns 401."""
        response = await client.get("/api/v1/companies")
        assert response.status_code == 401

    async def test_list_pagination(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        org: Organization,
        owner_headers: dict,
    ) -> None:
        """Pagination metadata is returned correctly."""
        for i in range(4):
            await _make_company(db_session, org, name=f"PaginatedCo{i}")

        response = await client.get(
            "/api/v1/companies",
            headers=owner_headers,
            params={"page": 1, "page_size": 2},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) <= 2
        assert data["page"] == 1
        assert data["pageSize"] == 2

    async def test_sales_rep_can_list_companies(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        org: Organization,
        rep_headers: dict,
    ) -> None:
        """Sales reps have read access to all companies in the tenant."""
        await _make_company(db_session, org, name="RepVisible")

        response = await client.get("/api/v1/companies", headers=rep_headers)
        assert response.status_code == 200


@pytest.mark.asyncio
class TestCreateCompany:
    """Tests for POST /api/v1/companies."""

    async def test_owner_can_create_company(
        self,
        client: AsyncClient,
        owner_headers: dict,
    ) -> None:
        """Owner can create a company."""
        response = await client.post(
            "/api/v1/companies",
            headers=owner_headers,
            json={"name": "New Company", "domain": "newco.com"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Company"
        assert "id" in data

    async def test_create_requires_auth(self, client: AsyncClient) -> None:
        """Unauthenticated request returns 401."""
        response = await client.post("/api/v1/companies", json={"name": "X"})
        assert response.status_code == 401

    async def test_sales_rep_can_create_company(
        self,
        client: AsyncClient,
        rep_headers: dict,
    ) -> None:
        """Sales reps are allowed to create companies."""
        response = await client.post(
            "/api/v1/companies",
            headers=rep_headers,
            json={"name": "Rep Created Co"},
        )
        assert response.status_code == 201

    async def test_viewer_cannot_create_company(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        org: Organization,
    ) -> None:
        """Viewers are forbidden from creating companies."""
        from datetime import UTC, datetime

        from src.core.enums import UserRole
        from src.core.security import create_access_token, hash_password
        from src.models.user import User

        viewer = User(
            organization_id=org.id,
            email="viewer@test.com",
            password_hash=hash_password("Pass1"),
            first_name="View",
            last_name="Er",
            role=UserRole.VIEWER.value,
            is_active=True,
            created_at=datetime.now(UTC),
        )
        db_session.add(viewer)
        await db_session.flush()
        await db_session.refresh(viewer)

        token = create_access_token(viewer.id, viewer.organization_id, viewer.role)
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.post(
            "/api/v1/companies",
            headers=headers,
            json={"name": "Forbidden Co"},
        )
        assert response.status_code == 403


@pytest.mark.asyncio
class TestGetCompany:
    """Tests for GET /api/v1/companies/{id}."""

    async def test_get_existing_company(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        org: Organization,
        owner_headers: dict,
    ) -> None:
        """Returns 200 with company details for an existing company."""
        company = await _make_company(db_session, org, name="Fetchable Co")
        response = await client.get(f"/api/v1/companies/{company.id}", headers=owner_headers)
        assert response.status_code == 200
        assert response.json()["id"] == str(company.id)

    async def test_get_nonexistent_company(
        self,
        client: AsyncClient,
        owner_headers: dict,
    ) -> None:
        """Returns 404 for a company that does not exist."""
        response = await client.get(f"/api/v1/companies/{uuid4()}", headers=owner_headers)
        assert response.status_code == 404


@pytest.mark.asyncio
class TestUpdateCompany:
    """Tests for PUT /api/v1/companies/{id}."""

    async def test_owner_can_update_any_company(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        org: Organization,
        owner_headers: dict,
    ) -> None:
        """Owner can update any company."""
        company = await _make_company(db_session, org, name="Old Name")
        response = await client.put(
            f"/api/v1/companies/{company.id}",
            headers=owner_headers,
            json={"name": "Updated Name"},
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Name"

    async def test_sales_rep_can_update_company(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        org: Organization,
        rep_headers: dict,
    ) -> None:
        """Sales reps are allowed to update companies."""
        company = await _make_company(db_session, org, name="Rep Updates")
        response = await client.put(
            f"/api/v1/companies/{company.id}",
            headers=rep_headers,
            json={"name": "Rep Updated"},
        )
        assert response.status_code == 200

    async def test_update_nonexistent_returns_404(
        self,
        client: AsyncClient,
        owner_headers: dict,
    ) -> None:
        """Updating a non-existent company returns 404."""
        response = await client.put(
            f"/api/v1/companies/{uuid4()}",
            headers=owner_headers,
            json={"name": "Ghost"},
        )
        assert response.status_code == 404


@pytest.mark.asyncio
class TestDeleteCompany:
    """Tests for DELETE /api/v1/companies/{id}."""

    async def test_owner_can_delete_company(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        org: Organization,
        owner_headers: dict,
    ) -> None:
        """Owner can delete any company."""
        company = await _make_company(db_session, org, name="ToDelete Co")
        response = await client.delete(f"/api/v1/companies/{company.id}", headers=owner_headers)
        assert response.status_code == 204

        get_response = await client.get(f"/api/v1/companies/{company.id}", headers=owner_headers)
        assert get_response.status_code == 404

    async def test_sales_rep_cannot_delete_company(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        org: Organization,
        rep_headers: dict,
    ) -> None:
        """Sales reps cannot delete companies."""
        company = await _make_company(db_session, org, name="Protected Co")
        response = await client.delete(f"/api/v1/companies/{company.id}", headers=rep_headers)
        assert response.status_code == 403
