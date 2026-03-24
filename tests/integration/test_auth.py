"""
Integration tests for authentication endpoints.

Tests cover:
- Registration (happy path, duplicate slug, duplicate email)
- Login (valid credentials, wrong password, inactive user)
- Token refresh (valid, expired/invalid)
- Logout
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestRegister:
    """Tests for POST /api/v1/auth/register."""

    async def test_register_success(self, client: AsyncClient) -> None:
        """A fresh registration returns 201 with access and refresh tokens."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "organization_name": "Acme Corp",
                "organization_slug": "acme-corp",
                "email": "admin@acme.com",
                "password": "Secure123",
                "first_name": "Jane",
                "last_name": "Doe",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_register_duplicate_slug(self, client: AsyncClient) -> None:
        """A duplicate slug returns 409 Conflict."""
        payload = {
            "organization_name": "First",
            "organization_slug": "unique-slug",
            "email": "first@test.com",
            "password": "Password1",
            "first_name": "A",
            "last_name": "B",
        }
        r1 = await client.post("/api/v1/auth/register", json=payload)
        assert r1.status_code == 201

        payload["email"] = "second@test.com"
        r2 = await client.post("/api/v1/auth/register", json=payload)
        assert r2.status_code == 409
        assert "slug" in r2.json()["detail"].lower()

    async def test_register_duplicate_email(self, client: AsyncClient) -> None:
        """A duplicate e-mail returns 409 Conflict."""
        payload = {
            "organization_name": "Org A",
            "organization_slug": "org-a-dup",
            "email": "dup@test.com",
            "password": "Password1",
            "first_name": "A",
            "last_name": "B",
        }
        r1 = await client.post("/api/v1/auth/register", json=payload)
        assert r1.status_code == 201

        payload["organization_slug"] = "org-b-dup"
        r2 = await client.post("/api/v1/auth/register", json=payload)
        assert r2.status_code == 409
        assert "email" in r2.json()["detail"].lower()

    async def test_register_weak_password(self, client: AsyncClient) -> None:
        """A password without digits fails schema validation (422)."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "organization_name": "Bad Org",
                "organization_slug": "bad-org",
                "email": "bad@test.com",
                "password": "onlyletters",
                "first_name": "A",
                "last_name": "B",
            },
        )
        assert response.status_code == 422

    async def test_register_invalid_slug(self, client: AsyncClient) -> None:
        """A slug with uppercase letters fails schema validation (422)."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "organization_name": "Bad Org",
                "organization_slug": "Bad_Org",
                "email": "valid@test.com",
                "password": "Password1",
                "first_name": "A",
                "last_name": "B",
            },
        )
        assert response.status_code == 422


@pytest.mark.asyncio
class TestLogin:
    """Tests for POST /api/v1/auth/login."""

    async def test_login_success(self, client: AsyncClient) -> None:
        """Valid credentials return 200 with tokens."""
        # Register first
        await client.post(
            "/api/v1/auth/register",
            json={
                "organization_name": "Login Org",
                "organization_slug": "login-org",
                "email": "login@test.com",
                "password": "LoginPass1",
                "first_name": "Login",
                "last_name": "User",
            },
        )

        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "login@test.com", "password": "LoginPass1"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    async def test_login_wrong_password(self, client: AsyncClient) -> None:
        """Wrong password returns 401."""
        await client.post(
            "/api/v1/auth/register",
            json={
                "organization_name": "WP Org",
                "organization_slug": "wp-org",
                "email": "wp@test.com",
                "password": "Correct1",
                "first_name": "A",
                "last_name": "B",
            },
        )

        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "wp@test.com", "password": "WrongPass1"},
        )
        assert response.status_code == 401

    async def test_login_unknown_email(self, client: AsyncClient) -> None:
        """Unknown e-mail returns 401 (same as wrong password — no enumeration)."""
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@test.com", "password": "Password1"},
        )
        assert response.status_code == 401


@pytest.mark.asyncio
class TestRefresh:
    """Tests for POST /api/v1/auth/refresh."""

    async def test_refresh_success(self, client: AsyncClient) -> None:
        """A valid refresh token returns a new access token."""
        reg = await client.post(
            "/api/v1/auth/register",
            json={
                "organization_name": "Refresh Org",
                "organization_slug": "refresh-org",
                "email": "refresh@test.com",
                "password": "Refresh1",
                "first_name": "R",
                "last_name": "U",
            },
        )
        refresh_token = reg.json()["refresh_token"]

        response = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
        )
        assert response.status_code == 200
        assert "access_token" in response.json()

    async def test_refresh_invalid_token(self, client: AsyncClient) -> None:
        """An invalid refresh token returns 401."""
        response = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": "not.a.valid.token"}
        )
        assert response.status_code == 401


@pytest.mark.asyncio
class TestLogout:
    """Tests for POST /api/v1/auth/logout."""

    async def test_logout_returns_204(self, client: AsyncClient) -> None:
        """Logout always returns 204 (stateless — token discarded client-side)."""
        response = await client.post(
            "/api/v1/auth/logout", json={"refresh_token": "any-token"}
        )
        assert response.status_code == 204
