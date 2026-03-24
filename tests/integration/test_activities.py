"""
Integration tests for activity CRUD endpoints.

Tests cover:
- List activities (pagination, owner vs sales rep scope, type filtering)
- Create activity (owner success, viewer forbidden)
- Get activity by ID
- Update activity (owner success, sales rep own vs other)
- Delete activity (owner success, sales rep own vs other)
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.activity import Activity
from src.models.organization import Organization
from src.models.user import User


async def _make_activity(
    session: AsyncSession,
    org: Organization,
    user: User,
    *,
    subject: str = "Test Activity",
    activity_type: str = "note",
) -> Activity:
    """Helper to persist an Activity directly via the ORM."""
    from datetime import UTC, datetime

    activity = Activity(
        organization_id=org.id,
        user_id=user.id,
        type=activity_type,
        subject=subject,
        created_at=datetime.now(UTC),
    )
    session.add(activity)
    await session.flush()
    await session.refresh(activity)
    return activity


@pytest.mark.asyncio
class TestListActivities:
    """Tests for GET /api/v1/activities."""

    async def test_owner_sees_all_activities(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        org: Organization,
        owner_user: User,
        sales_rep_user: User,
        owner_headers: dict,
    ) -> None:
        """Owner sees all activities in the organization."""
        await _make_activity(db_session, org, owner_user, subject="Owner Act")
        await _make_activity(db_session, org, sales_rep_user, subject="Rep Act")

        response = await client.get("/api/v1/activities", headers=owner_headers)
        assert response.status_code == 200
        assert response.json()["total"] >= 2

    async def test_sales_rep_sees_only_own_activities(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        org: Organization,
        owner_user: User,
        sales_rep_user: User,
        rep_headers: dict,
    ) -> None:
        """Sales rep only sees activities they own."""
        await _make_activity(db_session, org, sales_rep_user, subject="Mine")
        await _make_activity(db_session, org, owner_user, subject="Not Mine")

        response = await client.get("/api/v1/activities", headers=rep_headers)
        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["userId"] == str(sales_rep_user.id)

    async def test_list_requires_auth(self, client: AsyncClient) -> None:
        """Unauthenticated request returns 401."""
        response = await client.get("/api/v1/activities")
        assert response.status_code == 401

    async def test_filter_by_type(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        org: Organization,
        owner_user: User,
        owner_headers: dict,
    ) -> None:
        """Filtering by activity_type only returns activities of that type."""
        await _make_activity(db_session, org, owner_user, subject="Call Act", activity_type="call")
        await _make_activity(db_session, org, owner_user, subject="Note Act", activity_type="note")

        response = await client.get(
            "/api/v1/activities",
            headers=owner_headers,
            params={"activity_type": "call"},
        )
        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["type"] == "call"

    async def test_list_pagination(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        org: Organization,
        owner_user: User,
        owner_headers: dict,
    ) -> None:
        """Pagination metadata is correct."""
        for i in range(4):
            await _make_activity(db_session, org, owner_user, subject=f"Page Act {i}")

        response = await client.get(
            "/api/v1/activities",
            headers=owner_headers,
            params={"page": 1, "page_size": 2},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) <= 2
        assert data["page"] == 1
        assert data["pageSize"] == 2


@pytest.mark.asyncio
class TestCreateActivity:
    """Tests for POST /api/v1/activities."""

    async def test_owner_can_create_activity(
        self,
        client: AsyncClient,
        owner_headers: dict,
    ) -> None:
        """Owner can create an activity."""
        response = await client.post(
            "/api/v1/activities",
            headers=owner_headers,
            json={"type": "call", "subject": "Follow-up call"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["subject"] == "Follow-up call"
        assert data["type"] == "call"

    async def test_sales_rep_can_create_activity(
        self,
        client: AsyncClient,
        rep_headers: dict,
    ) -> None:
        """Sales reps can create activities."""
        response = await client.post(
            "/api/v1/activities",
            headers=rep_headers,
            json={"type": "email", "subject": "Sent proposal"},
        )
        assert response.status_code == 201

    async def test_viewer_cannot_create_activity(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        org: Organization,
    ) -> None:
        """Viewers are forbidden from creating activities."""
        from datetime import UTC, datetime

        from src.core.enums import UserRole
        from src.core.security import create_access_token, hash_password
        from src.models.user import User

        viewer = User(
            organization_id=org.id,
            email="activity.viewer@test.com",
            password_hash=hash_password("Pass1"),
            first_name="View",
            last_name="Act",
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
            "/api/v1/activities",
            headers=headers,
            json={"type": "note", "subject": "Forbidden note"},
        )
        assert response.status_code == 403

    async def test_create_requires_auth(self, client: AsyncClient) -> None:
        """Unauthenticated request returns 401."""
        response = await client.post(
            "/api/v1/activities",
            json={"type": "note", "subject": "No auth"},
        )
        assert response.status_code == 401


@pytest.mark.asyncio
class TestGetActivity:
    """Tests for GET /api/v1/activities/{id}."""

    async def test_get_existing_activity(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        org: Organization,
        owner_user: User,
        owner_headers: dict,
    ) -> None:
        """Returns 200 with activity details."""
        activity = await _make_activity(db_session, org, owner_user, subject="Fetchable")
        response = await client.get(f"/api/v1/activities/{activity.id}", headers=owner_headers)
        assert response.status_code == 200
        assert response.json()["id"] == str(activity.id)

    async def test_get_nonexistent_activity(
        self,
        client: AsyncClient,
        owner_headers: dict,
    ) -> None:
        """Returns 404 for an activity that does not exist."""
        response = await client.get(f"/api/v1/activities/{uuid4()}", headers=owner_headers)
        assert response.status_code == 404


@pytest.mark.asyncio
class TestUpdateActivity:
    """Tests for PUT /api/v1/activities/{id}."""

    async def test_owner_can_update_any_activity(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        org: Organization,
        owner_user: User,
        owner_headers: dict,
    ) -> None:
        """Owner can update any activity."""
        activity = await _make_activity(db_session, org, owner_user, subject="Old Subject")
        response = await client.put(
            f"/api/v1/activities/{activity.id}",
            headers=owner_headers,
            json={"subject": "New Subject"},
        )
        assert response.status_code == 200
        assert response.json()["subject"] == "New Subject"

    async def test_sales_rep_cannot_update_others_activity(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        org: Organization,
        owner_user: User,
        rep_headers: dict,
    ) -> None:
        """Sales rep cannot update an activity they do not own."""
        activity = await _make_activity(db_session, org, owner_user, subject="Owner's Activity")
        response = await client.put(
            f"/api/v1/activities/{activity.id}",
            headers=rep_headers,
            json={"subject": "Hijacked"},
        )
        assert response.status_code == 403

    async def test_sales_rep_can_update_own_activity(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        org: Organization,
        sales_rep_user: User,
        rep_headers: dict,
    ) -> None:
        """Sales rep can update their own activity."""
        activity = await _make_activity(db_session, org, sales_rep_user, subject="My Activity")
        response = await client.put(
            f"/api/v1/activities/{activity.id}",
            headers=rep_headers,
            json={"subject": "Updated Mine"},
        )
        assert response.status_code == 200
        assert response.json()["subject"] == "Updated Mine"


@pytest.mark.asyncio
class TestDeleteActivity:
    """Tests for DELETE /api/v1/activities/{id}."""

    async def test_owner_can_delete_any_activity(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        org: Organization,
        owner_user: User,
        owner_headers: dict,
    ) -> None:
        """Owner can delete any activity."""
        activity = await _make_activity(db_session, org, owner_user, subject="To Delete")
        response = await client.delete(f"/api/v1/activities/{activity.id}", headers=owner_headers)
        assert response.status_code == 204

        get_response = await client.get(f"/api/v1/activities/{activity.id}", headers=owner_headers)
        assert get_response.status_code == 404

    async def test_sales_rep_cannot_delete_others_activity(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        org: Organization,
        owner_user: User,
        rep_headers: dict,
    ) -> None:
        """Sales rep cannot delete an activity owned by someone else."""
        activity = await _make_activity(db_session, org, owner_user, subject="Protected")
        response = await client.delete(f"/api/v1/activities/{activity.id}", headers=rep_headers)
        assert response.status_code == 403

    async def test_sales_rep_can_delete_own_activity(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        org: Organization,
        sales_rep_user: User,
        rep_headers: dict,
    ) -> None:
        """Sales rep can delete their own activity."""
        activity = await _make_activity(db_session, org, sales_rep_user, subject="Delete My Own")
        response = await client.delete(f"/api/v1/activities/{activity.id}", headers=rep_headers)
        assert response.status_code == 204
