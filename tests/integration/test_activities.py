"""
Integration tests for activity CRUD endpoints.

All repository calls are mocked — no PostgreSQL required.

Tests cover:
- GET  /api/v1/activities              (list)
- POST /api/v1/activities              (success, forbidden viewer)
- GET  /api/v1/activities/{id}         (success, 404)
- PUT  /api/v1/activities/{id}         (owner success, forbidden rep, 404)
- DELETE /api/v1/activities/{id}       (owner success, forbidden rep, 404)
"""

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient

from src.schemas.activity import ActivityResponse
from tests.integration.conftest import make_activity

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ACTIVITY_PAYLOAD = {
    "type": "call",
    "subject": "Follow-up call",
}


def _paginated(items: list) -> SimpleNamespace:
    validated = [ActivityResponse.model_validate(i) for i in items]
    return SimpleNamespace(
        items=validated,
        total=len(items),
        page=1,
        page_size=20,
        pages=1,
    )


# ---------------------------------------------------------------------------
# List activities
# ---------------------------------------------------------------------------


class TestListActivities:
    """GET /api/v1/activities"""

    @patch("src.api.v1.routers.activities.ActivityService")
    async def test_list_returns_200(
        self, mock_svc_cls: AsyncMock, client_owner: AsyncClient
    ) -> None:
        """Owner gets a paginated list of activities."""
        activity = make_activity()
        mock_svc_cls.return_value.list_activities = AsyncMock(return_value=_paginated([activity]))

        response = await client_owner.get("/api/v1/activities")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1

    @patch("src.api.v1.routers.activities.ActivityService")
    async def test_list_empty(self, mock_svc_cls: AsyncMock, client_owner: AsyncClient) -> None:
        """Empty tenant returns empty list."""
        mock_svc_cls.return_value.list_activities = AsyncMock(return_value=_paginated([]))

        response = await client_owner.get("/api/v1/activities")

        assert response.status_code == 200
        assert response.json()["total"] == 0

    @patch("src.api.v1.routers.activities.ActivityService")
    async def test_list_with_type_filter(
        self, mock_svc_cls: AsyncMock, client_owner: AsyncClient
    ) -> None:
        """Filtering by activity type returns filtered results."""
        activity = make_activity(activity_type="call")
        mock_svc_cls.return_value.list_activities = AsyncMock(return_value=_paginated([activity]))

        response = await client_owner.get("/api/v1/activities?activity_type=call")

        assert response.status_code == 200

    async def test_list_unauthenticated(self, client_no_auth: AsyncClient) -> None:
        """Unauthenticated request returns 401."""
        response = await client_no_auth.get("/api/v1/activities")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Create activity
# ---------------------------------------------------------------------------


class TestCreateActivity:
    """POST /api/v1/activities"""

    @patch("src.api.v1.routers.activities.ActivityService")
    async def test_create_success_owner(
        self, mock_svc_cls: AsyncMock, client_owner: AsyncClient
    ) -> None:
        """Owner can create an activity — returns 201."""
        activity = make_activity()
        mock_svc_cls.return_value.create_activity = AsyncMock(return_value=activity)

        response = await client_owner.post("/api/v1/activities", json=_ACTIVITY_PAYLOAD)

        assert response.status_code == 201
        assert response.json()["subject"] == activity.subject

    @patch("src.api.v1.routers.activities.ActivityService")
    async def test_create_success_rep(
        self, mock_svc_cls: AsyncMock, client_rep: AsyncClient
    ) -> None:
        """Sales rep can create an activity."""
        activity = make_activity()
        mock_svc_cls.return_value.create_activity = AsyncMock(return_value=activity)

        response = await client_rep.post("/api/v1/activities", json=_ACTIVITY_PAYLOAD)

        assert response.status_code == 201

    @patch("src.api.v1.routers.activities.ActivityService")
    async def test_create_forbidden_viewer(
        self, mock_svc_cls: AsyncMock, client_viewer: AsyncClient
    ) -> None:
        """Viewer cannot create activities — 403."""
        from src.core.exceptions import ForbiddenError

        mock_svc_cls.return_value.create_activity = AsyncMock(
            side_effect=ForbiddenError("Viewers cannot create activities")
        )

        response = await client_viewer.post("/api/v1/activities", json=_ACTIVITY_PAYLOAD)

        assert response.status_code == 403

    async def test_create_missing_required_fields(self, client_owner: AsyncClient) -> None:
        """Missing required fields return 422."""
        response = await client_owner.post("/api/v1/activities", json={})
        assert response.status_code == 422

    async def test_create_invalid_type(self, client_owner: AsyncClient) -> None:
        """Invalid activity type returns 422."""
        response = await client_owner.post(
            "/api/v1/activities",
            json={"type": "invalid_type", "subject": "Test"},
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Get activity
# ---------------------------------------------------------------------------


class TestGetActivity:
    """GET /api/v1/activities/{activity_id}"""

    @patch("src.api.v1.routers.activities.ActivityService")
    async def test_get_success(self, mock_svc_cls: AsyncMock, client_owner: AsyncClient) -> None:
        """Returns 200 with the activity data."""
        activity_id = uuid.uuid4()
        activity = make_activity(activity_id=activity_id)
        mock_svc_cls.return_value.get_activity = AsyncMock(return_value=activity)

        response = await client_owner.get(f"/api/v1/activities/{activity_id}")

        assert response.status_code == 200
        assert response.json()["id"] == str(activity_id)

    @patch("src.api.v1.routers.activities.ActivityService")
    async def test_get_not_found(self, mock_svc_cls: AsyncMock, client_owner: AsyncClient) -> None:
        """Non-existent activity returns 404."""
        from src.core.exceptions import NotFoundError

        activity_id = uuid.uuid4()
        mock_svc_cls.return_value.get_activity = AsyncMock(
            side_effect=NotFoundError("Activity", str(activity_id))
        )

        response = await client_owner.get(f"/api/v1/activities/{activity_id}")

        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Update activity
# ---------------------------------------------------------------------------


class TestUpdateActivity:
    """PUT /api/v1/activities/{activity_id}"""

    @patch("src.api.v1.routers.activities.ActivityService")
    async def test_update_success(self, mock_svc_cls: AsyncMock, client_owner: AsyncClient) -> None:
        """Owner can update an activity — returns 200."""
        activity_id = uuid.uuid4()
        updated = make_activity(activity_id=activity_id, subject="Updated subject")
        mock_svc_cls.return_value.update_activity = AsyncMock(return_value=updated)

        response = await client_owner.put(
            f"/api/v1/activities/{activity_id}",
            json={"subject": "Updated subject"},
        )

        assert response.status_code == 200
        assert response.json()["subject"] == "Updated subject"

    @patch("src.api.v1.routers.activities.ActivityService")
    async def test_update_not_found(
        self, mock_svc_cls: AsyncMock, client_owner: AsyncClient
    ) -> None:
        """Updating a non-existent activity returns 404."""
        from src.core.exceptions import NotFoundError

        activity_id = uuid.uuid4()
        mock_svc_cls.return_value.update_activity = AsyncMock(
            side_effect=NotFoundError("Activity", str(activity_id))
        )

        response = await client_owner.put(
            f"/api/v1/activities/{activity_id}",
            json={"subject": "X"},
        )

        assert response.status_code == 404

    @patch("src.api.v1.routers.activities.ActivityService")
    async def test_update_forbidden_rep(
        self, mock_svc_cls: AsyncMock, client_rep: AsyncClient
    ) -> None:
        """Sales rep cannot modify another user's activity — 403."""
        from src.core.exceptions import ForbiddenError

        activity_id = uuid.uuid4()
        mock_svc_cls.return_value.update_activity = AsyncMock(
            side_effect=ForbiddenError("Sales reps can only modify their own activities")
        )

        response = await client_rep.put(
            f"/api/v1/activities/{activity_id}",
            json={"subject": "X"},
        )

        assert response.status_code == 403


# ---------------------------------------------------------------------------
# Delete activity
# ---------------------------------------------------------------------------


class TestDeleteActivity:
    """DELETE /api/v1/activities/{activity_id}"""

    @patch("src.api.v1.routers.activities.ActivityService")
    async def test_delete_success(self, mock_svc_cls: AsyncMock, client_owner: AsyncClient) -> None:
        """Owner can delete an activity — returns 204."""
        activity_id = uuid.uuid4()
        mock_svc_cls.return_value.delete_activity = AsyncMock(return_value=None)

        response = await client_owner.delete(f"/api/v1/activities/{activity_id}")

        assert response.status_code == 204

    @patch("src.api.v1.routers.activities.ActivityService")
    async def test_delete_forbidden_rep(
        self, mock_svc_cls: AsyncMock, client_rep: AsyncClient
    ) -> None:
        """Sales rep cannot delete another user's activity — 403."""
        from src.core.exceptions import ForbiddenError

        activity_id = uuid.uuid4()
        mock_svc_cls.return_value.delete_activity = AsyncMock(
            side_effect=ForbiddenError("Sales reps can only modify their own activities")
        )

        response = await client_rep.delete(f"/api/v1/activities/{activity_id}")

        assert response.status_code == 403

    @patch("src.api.v1.routers.activities.ActivityService")
    async def test_delete_not_found(
        self, mock_svc_cls: AsyncMock, client_owner: AsyncClient
    ) -> None:
        """Deleting a non-existent activity returns 404."""
        from src.core.exceptions import NotFoundError

        activity_id = uuid.uuid4()
        mock_svc_cls.return_value.delete_activity = AsyncMock(
            side_effect=NotFoundError("Activity", str(activity_id))
        )

        response = await client_owner.delete(f"/api/v1/activities/{activity_id}")

        assert response.status_code == 404
