"""
Integration tests for company CRUD endpoints.

All repository calls are mocked — no PostgreSQL required.

Tests cover:
- GET  /api/v1/companies              (list)
- POST /api/v1/companies              (success, forbidden for viewer)
- GET  /api/v1/companies/{id}         (success, 404)
- PUT  /api/v1/companies/{id}         (owner success, 404)
- DELETE /api/v1/companies/{id}       (owner success, forbidden for rep)
- GET  /api/v1/companies/{id}/contacts
"""

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient

from src.schemas.company import CompanyResponse
from tests.integration.conftest import make_company, make_contact

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_COMPANY_PAYLOAD = {
    "name": "Acme Corp",
    "domain": "acme.com",
    "industry": "Technology",
}


def _paginated(items: list) -> SimpleNamespace:
    validated = [CompanyResponse.model_validate(i) for i in items]
    return SimpleNamespace(
        items=validated,
        total=len(items),
        page=1,
        page_size=20,
        pages=1,
    )


# ---------------------------------------------------------------------------
# List companies
# ---------------------------------------------------------------------------


class TestListCompanies:
    """GET /api/v1/companies"""

    @patch("src.api.v1.routers.companies.CompanyService")
    async def test_list_returns_200(
        self, mock_svc_cls: AsyncMock, client_owner: AsyncClient
    ) -> None:
        """Owner gets a paginated list of companies."""
        company = make_company()
        mock_svc_cls.return_value.list_companies = AsyncMock(return_value=_paginated([company]))

        response = await client_owner.get("/api/v1/companies")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1

    @patch("src.api.v1.routers.companies.CompanyService")
    async def test_list_empty(self, mock_svc_cls: AsyncMock, client_owner: AsyncClient) -> None:
        """Empty tenant returns empty items list."""
        mock_svc_cls.return_value.list_companies = AsyncMock(return_value=_paginated([]))

        response = await client_owner.get("/api/v1/companies")

        assert response.status_code == 200
        assert response.json()["total"] == 0

    async def test_list_unauthenticated(self, client_no_auth: AsyncClient) -> None:
        """Unauthenticated request returns 401."""
        response = await client_no_auth.get("/api/v1/companies")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Create company
# ---------------------------------------------------------------------------


class TestCreateCompany:
    """POST /api/v1/companies"""

    @patch("src.api.v1.routers.companies.CompanyService")
    async def test_create_success_owner(
        self, mock_svc_cls: AsyncMock, client_owner: AsyncClient
    ) -> None:
        """Owner can create a company — returns 201."""
        company = make_company()
        mock_svc_cls.return_value.create_company = AsyncMock(return_value=company)

        response = await client_owner.post("/api/v1/companies", json=_COMPANY_PAYLOAD)

        assert response.status_code == 201
        assert response.json()["name"] == company.name

    @patch("src.api.v1.routers.companies.CompanyService")
    async def test_create_success_rep(
        self, mock_svc_cls: AsyncMock, client_rep: AsyncClient
    ) -> None:
        """Sales rep can create a company."""
        company = make_company()
        mock_svc_cls.return_value.create_company = AsyncMock(return_value=company)

        response = await client_rep.post("/api/v1/companies", json=_COMPANY_PAYLOAD)

        assert response.status_code == 201

    @patch("src.api.v1.routers.companies.CompanyService")
    async def test_create_forbidden_viewer(
        self, mock_svc_cls: AsyncMock, client_viewer: AsyncClient
    ) -> None:
        """Viewer cannot create companies — 403."""
        from src.core.exceptions import ForbiddenError

        mock_svc_cls.return_value.create_company = AsyncMock(
            side_effect=ForbiddenError("Viewers cannot create companies")
        )

        response = await client_viewer.post("/api/v1/companies", json=_COMPANY_PAYLOAD)

        assert response.status_code == 403

    async def test_create_missing_name(self, client_owner: AsyncClient) -> None:
        """Missing required 'name' field returns 422."""
        response = await client_owner.post("/api/v1/companies", json={"domain": "acme.com"})
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Get company
# ---------------------------------------------------------------------------


class TestGetCompany:
    """GET /api/v1/companies/{company_id}"""

    @patch("src.api.v1.routers.companies.CompanyService")
    async def test_get_success(self, mock_svc_cls: AsyncMock, client_owner: AsyncClient) -> None:
        """Returns 200 with the company data."""
        company_id = uuid.uuid4()
        company = make_company(company_id=company_id)
        mock_svc_cls.return_value.get_company = AsyncMock(return_value=company)

        response = await client_owner.get(f"/api/v1/companies/{company_id}")

        assert response.status_code == 200
        assert response.json()["id"] == str(company_id)

    @patch("src.api.v1.routers.companies.CompanyService")
    async def test_get_not_found(self, mock_svc_cls: AsyncMock, client_owner: AsyncClient) -> None:
        """Non-existent company returns 404."""
        from src.core.exceptions import NotFoundError

        company_id = uuid.uuid4()
        mock_svc_cls.return_value.get_company = AsyncMock(
            side_effect=NotFoundError("Company", str(company_id))
        )

        response = await client_owner.get(f"/api/v1/companies/{company_id}")

        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Update company
# ---------------------------------------------------------------------------


class TestUpdateCompany:
    """PUT /api/v1/companies/{company_id}"""

    @patch("src.api.v1.routers.companies.CompanyService")
    async def test_update_success(self, mock_svc_cls: AsyncMock, client_owner: AsyncClient) -> None:
        """Owner can update a company — returns 200."""
        company_id = uuid.uuid4()
        updated = make_company(company_id=company_id, name="Updated Corp")
        mock_svc_cls.return_value.update_company = AsyncMock(return_value=updated)

        response = await client_owner.put(
            f"/api/v1/companies/{company_id}", json={"name": "Updated Corp"}
        )

        assert response.status_code == 200
        assert response.json()["name"] == "Updated Corp"

    @patch("src.api.v1.routers.companies.CompanyService")
    async def test_update_not_found(
        self, mock_svc_cls: AsyncMock, client_owner: AsyncClient
    ) -> None:
        """Updating a non-existent company returns 404."""
        from src.core.exceptions import NotFoundError

        company_id = uuid.uuid4()
        mock_svc_cls.return_value.update_company = AsyncMock(
            side_effect=NotFoundError("Company", str(company_id))
        )

        response = await client_owner.put(f"/api/v1/companies/{company_id}", json={"name": "X"})

        assert response.status_code == 404

    @patch("src.api.v1.routers.companies.CompanyService")
    async def test_update_forbidden_viewer(
        self, mock_svc_cls: AsyncMock, client_viewer: AsyncClient
    ) -> None:
        """Viewer cannot update a company — 403."""
        from src.core.exceptions import ForbiddenError

        company_id = uuid.uuid4()
        mock_svc_cls.return_value.update_company = AsyncMock(
            side_effect=ForbiddenError("Viewers cannot update companies")
        )

        response = await client_viewer.put(f"/api/v1/companies/{company_id}", json={"name": "X"})

        assert response.status_code == 403


# ---------------------------------------------------------------------------
# Delete company
# ---------------------------------------------------------------------------


class TestDeleteCompany:
    """DELETE /api/v1/companies/{company_id}"""

    @patch("src.api.v1.routers.companies.CompanyService")
    async def test_delete_success(self, mock_svc_cls: AsyncMock, client_owner: AsyncClient) -> None:
        """Owner can delete a company — returns 204."""
        company_id = uuid.uuid4()
        mock_svc_cls.return_value.delete_company = AsyncMock(return_value=None)

        response = await client_owner.delete(f"/api/v1/companies/{company_id}")

        assert response.status_code == 204

    @patch("src.api.v1.routers.companies.CompanyService")
    async def test_delete_forbidden_for_rep(
        self, mock_svc_cls: AsyncMock, client_rep: AsyncClient
    ) -> None:
        """Sales rep cannot delete a company — 403."""
        from src.core.exceptions import ForbiddenError

        company_id = uuid.uuid4()
        mock_svc_cls.return_value.delete_company = AsyncMock(
            side_effect=ForbiddenError("Only owners and admins can delete companies")
        )

        response = await client_rep.delete(f"/api/v1/companies/{company_id}")

        assert response.status_code == 403

    @patch("src.api.v1.routers.companies.CompanyService")
    async def test_delete_not_found(
        self, mock_svc_cls: AsyncMock, client_owner: AsyncClient
    ) -> None:
        """Deleting a non-existent company returns 404."""
        from src.core.exceptions import NotFoundError

        company_id = uuid.uuid4()
        mock_svc_cls.return_value.delete_company = AsyncMock(
            side_effect=NotFoundError("Company", str(company_id))
        )

        response = await client_owner.delete(f"/api/v1/companies/{company_id}")

        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Company contacts sub-resource
# ---------------------------------------------------------------------------


class TestCompanyContacts:
    """GET /api/v1/companies/{company_id}/contacts"""

    @patch("src.api.v1.routers.companies.CompanyService")
    async def test_list_contacts_success(
        self, mock_svc_cls: AsyncMock, client_owner: AsyncClient
    ) -> None:
        """Returns the list of contacts linked to a company."""
        from src.schemas.contact import ContactResponse

        company_id = uuid.uuid4()
        contact = make_contact()
        contact_response = ContactResponse.model_validate(contact)
        mock_svc_cls.return_value.get_company_contacts = AsyncMock(return_value=[contact_response])

        response = await client_owner.get(f"/api/v1/companies/{company_id}/contacts")

        assert response.status_code == 200
        assert isinstance(response.json(), list)
        assert len(response.json()) == 1

    @patch("src.api.v1.routers.companies.CompanyService")
    async def test_list_contacts_company_not_found(
        self, mock_svc_cls: AsyncMock, client_owner: AsyncClient
    ) -> None:
        """Returns 404 when the company does not exist."""
        from src.core.exceptions import NotFoundError

        company_id = uuid.uuid4()
        mock_svc_cls.return_value.get_company_contacts = AsyncMock(
            side_effect=NotFoundError("Company", str(company_id))
        )

        response = await client_owner.get(f"/api/v1/companies/{company_id}/contacts")

        assert response.status_code == 404
