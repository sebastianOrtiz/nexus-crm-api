"""
Integration tests for authentication endpoints.

All repository calls are mocked — no PostgreSQL required.

Tests cover:
- POST /api/v1/auth/register  (success, duplicate slug, duplicate email,
  weak password, invalid slug)
- POST /api/v1/auth/login     (success, wrong password, unknown email)
- POST /api/v1/auth/refresh   (valid token, invalid token)
- POST /api/v1/auth/logout    (always 204)
"""

from unittest.mock import AsyncMock, patch

from httpx import AsyncClient

from src.core.enums import UserRole
from src.core.security import hash_password
from tests.integration.conftest import (
    ORG_ID,
    OWNER_ID,
    make_org,
    make_user,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_REGISTER_PAYLOAD = {
    "organization_name": "Acme Corp",
    "organization_slug": "acme-corp",
    "email": "admin@acme.com",
    "password": "Secure123",
    "first_name": "Jane",
    "last_name": "Doe",
}


# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------


class TestRegister:
    """POST /api/v1/auth/register"""

    @patch("src.services.auth.OrganizationRepository")
    @patch("src.services.auth.UserRepository")
    async def test_register_success(
        self,
        mock_user_repo_cls: AsyncMock,
        mock_org_repo_cls: AsyncMock,
        client_no_auth: AsyncClient,
    ) -> None:
        """A fresh registration returns 201 with access and refresh tokens."""
        org = make_org()
        user = make_user(user_id=OWNER_ID, org_id=ORG_ID, role=UserRole.OWNER)

        mock_org_repo_cls.return_value.get_by_slug = AsyncMock(return_value=None)
        mock_user_repo_cls.return_value.get_by_email = AsyncMock(return_value=None)
        mock_org_repo_cls.return_value.create = AsyncMock(return_value=org)
        mock_user_repo_cls.return_value.create = AsyncMock(return_value=user)

        response = await client_no_auth.post("/api/v1/auth/register", json=_REGISTER_PAYLOAD)

        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"  # noqa: S105

    @patch("src.services.auth.OrganizationRepository")
    @patch("src.services.auth.UserRepository")
    async def test_register_duplicate_slug(
        self,
        mock_user_repo_cls: AsyncMock,
        mock_org_repo_cls: AsyncMock,
        client_no_auth: AsyncClient,
    ) -> None:
        """A duplicate slug returns 409 Conflict."""
        existing_org = make_org(slug="acme-corp")
        mock_org_repo_cls.return_value.get_by_slug = AsyncMock(return_value=existing_org)
        mock_user_repo_cls.return_value.get_by_email = AsyncMock(return_value=None)

        response = await client_no_auth.post("/api/v1/auth/register", json=_REGISTER_PAYLOAD)

        assert response.status_code == 409
        assert "slug" in response.json()["detail"].lower()

    @patch("src.services.auth.OrganizationRepository")
    @patch("src.services.auth.UserRepository")
    async def test_register_duplicate_email(
        self,
        mock_user_repo_cls: AsyncMock,
        mock_org_repo_cls: AsyncMock,
        client_no_auth: AsyncClient,
    ) -> None:
        """A duplicate e-mail returns 409 Conflict."""
        existing_user = make_user(email="admin@acme.com")
        mock_org_repo_cls.return_value.get_by_slug = AsyncMock(return_value=None)
        mock_user_repo_cls.return_value.get_by_email = AsyncMock(return_value=existing_user)

        response = await client_no_auth.post("/api/v1/auth/register", json=_REGISTER_PAYLOAD)

        assert response.status_code == 409
        assert "email" in response.json()["detail"].lower()

    async def test_register_weak_password(self, client_no_auth: AsyncClient) -> None:
        """A password without digits fails schema validation (422)."""
        payload = {**_REGISTER_PAYLOAD, "password": "onlyletters"}
        response = await client_no_auth.post("/api/v1/auth/register", json=payload)
        assert response.status_code == 422

    async def test_register_invalid_slug(self, client_no_auth: AsyncClient) -> None:
        """A slug with uppercase letters fails schema validation (422)."""
        payload = {**_REGISTER_PAYLOAD, "organization_slug": "Bad_Org"}
        response = await client_no_auth.post("/api/v1/auth/register", json=payload)
        assert response.status_code == 422

    async def test_register_missing_fields(self, client_no_auth: AsyncClient) -> None:
        """Missing required fields return 422."""
        response = await client_no_auth.post("/api/v1/auth/register", json={})
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


class TestLogin:
    """POST /api/v1/auth/login"""

    @patch("src.services.auth.UserRepository")
    async def test_login_success(
        self,
        mock_user_repo_cls: AsyncMock,
        client_no_auth: AsyncClient,
    ) -> None:
        """Valid credentials return 200 with tokens."""
        user = make_user(email="login@test.com")
        user.password_hash = hash_password("LoginPass1")
        mock_user_repo_cls.return_value.get_by_email = AsyncMock(return_value=user)

        response = await client_no_auth.post(
            "/api/v1/auth/login",
            json={"email": "login@test.com", "password": "LoginPass1"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    @patch("src.services.auth.UserRepository")
    async def test_login_wrong_password(
        self,
        mock_user_repo_cls: AsyncMock,
        client_no_auth: AsyncClient,
    ) -> None:
        """Wrong password returns 401."""
        user = make_user(email="wp@test.com")
        user.password_hash = hash_password("CorrectPass1")
        mock_user_repo_cls.return_value.get_by_email = AsyncMock(return_value=user)

        response = await client_no_auth.post(
            "/api/v1/auth/login",
            json={"email": "wp@test.com", "password": "WrongPass1"},
        )

        assert response.status_code == 401

    @patch("src.services.auth.UserRepository")
    async def test_login_unknown_email(
        self,
        mock_user_repo_cls: AsyncMock,
        client_no_auth: AsyncClient,
    ) -> None:
        """Unknown e-mail returns 401 (no user enumeration)."""
        mock_user_repo_cls.return_value.get_by_email = AsyncMock(return_value=None)

        response = await client_no_auth.post(
            "/api/v1/auth/login",
            json={"email": "nobody@test.com", "password": "Password1"},
        )

        assert response.status_code == 401

    @patch("src.services.auth.UserRepository")
    async def test_login_inactive_user(
        self,
        mock_user_repo_cls: AsyncMock,
        client_no_auth: AsyncClient,
    ) -> None:
        """An inactive account returns 401."""
        user = make_user(email="inactive@test.com", is_active=False)
        user.password_hash = hash_password("Password1")
        mock_user_repo_cls.return_value.get_by_email = AsyncMock(return_value=user)

        response = await client_no_auth.post(
            "/api/v1/auth/login",
            json={"email": "inactive@test.com", "password": "Password1"},
        )

        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Refresh
# ---------------------------------------------------------------------------


class TestRefresh:
    """POST /api/v1/auth/refresh"""

    @patch("src.services.auth.UserRepository")
    async def test_refresh_success(
        self,
        mock_user_repo_cls: AsyncMock,
        client_no_auth: AsyncClient,
        owner_refresh_token: str,
    ) -> None:
        """A valid refresh token returns a new access token."""
        user = make_user(user_id=OWNER_ID, org_id=ORG_ID)
        mock_user_repo_cls.return_value.get_by_id = AsyncMock(return_value=user)

        response = await client_no_auth.post(
            "/api/v1/auth/refresh", json={"refresh_token": owner_refresh_token}
        )

        assert response.status_code == 200
        assert "access_token" in response.json()

    async def test_refresh_invalid_token(self, client_no_auth: AsyncClient) -> None:
        """An invalid refresh token returns 401."""
        response = await client_no_auth.post(
            "/api/v1/auth/refresh", json={"refresh_token": "not.a.valid.token"}
        )
        assert response.status_code == 401

    @patch("src.services.auth.UserRepository")
    async def test_refresh_deactivated_user(
        self,
        mock_user_repo_cls: AsyncMock,
        client_no_auth: AsyncClient,
        owner_refresh_token: str,
    ) -> None:
        """A refresh token for a deactivated user returns 401."""
        user = make_user(user_id=OWNER_ID, is_active=False)
        mock_user_repo_cls.return_value.get_by_id = AsyncMock(return_value=user)

        response = await client_no_auth.post(
            "/api/v1/auth/refresh", json={"refresh_token": owner_refresh_token}
        )

        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------


class TestLogout:
    """POST /api/v1/auth/logout"""

    async def test_logout_returns_204(self, client_no_auth: AsyncClient) -> None:
        """Logout always returns 204 (stateless — token discarded client-side)."""
        response = await client_no_auth.post(
            "/api/v1/auth/logout", json={"refresh_token": "any-token"}
        )
        assert response.status_code == 204
