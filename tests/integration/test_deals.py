"""
Integration tests for deal CRUD endpoints.

All repository calls are mocked — no PostgreSQL required.

Tests cover:
- GET  /api/v1/deals              (list)
- POST /api/v1/deals              (success, stage not found, forbidden viewer)
- GET  /api/v1/deals/{id}         (success, 404)
- PUT  /api/v1/deals/{id}         (owner success, forbidden rep, 404)
- PUT  /api/v1/deals/{id}/stage   (move stage)
- DELETE /api/v1/deals/{id}       (owner success, forbidden rep, 404)
"""

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient

from src.schemas.deal import DealResponse
from tests.integration.conftest import make_deal

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_STAGE_ID = uuid.UUID("00000000-0000-0000-0001-000000000001")


def _make_deal_payload(stage_id: uuid.UUID = _STAGE_ID) -> dict:
    return {
        "title": "Big Deal",
        "value": 10000.0,
        "currency": "USD",
        "stage_id": str(stage_id),
    }


def _paginated(items: list) -> SimpleNamespace:
    validated = [DealResponse.model_validate(i) for i in items]
    return SimpleNamespace(
        items=validated,
        total=len(items),
        page=1,
        page_size=20,
        pages=1,
    )


# ---------------------------------------------------------------------------
# List deals
# ---------------------------------------------------------------------------


class TestListDeals:
    """GET /api/v1/deals"""

    @patch("src.api.v1.routers.deals.DealService")
    async def test_list_returns_200(
        self, mock_svc_cls: AsyncMock, client_owner: AsyncClient
    ) -> None:
        """Owner gets a paginated list of deals."""
        deal = make_deal(stage_id=_STAGE_ID)
        mock_svc_cls.return_value.list_deals = AsyncMock(return_value=_paginated([deal]))

        response = await client_owner.get("/api/v1/deals")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1

    @patch("src.api.v1.routers.deals.DealService")
    async def test_list_empty(self, mock_svc_cls: AsyncMock, client_owner: AsyncClient) -> None:
        """Empty pipeline returns empty list."""
        mock_svc_cls.return_value.list_deals = AsyncMock(return_value=_paginated([]))

        response = await client_owner.get("/api/v1/deals")

        assert response.status_code == 200
        assert response.json()["total"] == 0

    async def test_list_unauthenticated(self, client_no_auth: AsyncClient) -> None:
        """Unauthenticated request returns 401."""
        response = await client_no_auth.get("/api/v1/deals")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Create deal
# ---------------------------------------------------------------------------


class TestCreateDeal:
    """POST /api/v1/deals"""

    @patch("src.api.v1.routers.deals.DealService")
    async def test_create_success(self, mock_svc_cls: AsyncMock, client_owner: AsyncClient) -> None:
        """Owner can create a deal — returns 201."""
        deal = make_deal(stage_id=_STAGE_ID)
        mock_svc_cls.return_value.create_deal = AsyncMock(return_value=deal)

        response = await client_owner.post("/api/v1/deals", json=_make_deal_payload())

        assert response.status_code == 201
        assert response.json()["title"] == deal.title

    @patch("src.api.v1.routers.deals.DealService")
    async def test_create_stage_not_found(
        self, mock_svc_cls: AsyncMock, client_owner: AsyncClient
    ) -> None:
        """Creating a deal with a non-existent stage returns 404."""
        from src.core.exceptions import NotFoundError

        mock_svc_cls.return_value.create_deal = AsyncMock(
            side_effect=NotFoundError("PipelineStage", str(_STAGE_ID))
        )

        response = await client_owner.post("/api/v1/deals", json=_make_deal_payload())

        assert response.status_code == 404

    @patch("src.api.v1.routers.deals.DealService")
    async def test_create_forbidden_viewer(
        self, mock_svc_cls: AsyncMock, client_viewer: AsyncClient
    ) -> None:
        """Viewer cannot create deals — 403."""
        from src.core.exceptions import ForbiddenError

        mock_svc_cls.return_value.create_deal = AsyncMock(
            side_effect=ForbiddenError("Viewers cannot create deals")
        )

        response = await client_viewer.post("/api/v1/deals", json=_make_deal_payload())

        assert response.status_code == 403

    async def test_create_missing_title(self, client_owner: AsyncClient) -> None:
        """Missing required 'title' field returns 422."""
        response = await client_owner.post("/api/v1/deals", json={"stage_id": str(_STAGE_ID)})
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Get deal
# ---------------------------------------------------------------------------


class TestGetDeal:
    """GET /api/v1/deals/{deal_id}"""

    @patch("src.api.v1.routers.deals.DealService")
    async def test_get_success(self, mock_svc_cls: AsyncMock, client_owner: AsyncClient) -> None:
        """Returns 200 with the deal data."""
        deal_id = uuid.uuid4()
        deal = make_deal(deal_id=deal_id, stage_id=_STAGE_ID)
        mock_svc_cls.return_value.get_deal = AsyncMock(return_value=deal)

        response = await client_owner.get(f"/api/v1/deals/{deal_id}")

        assert response.status_code == 200
        assert response.json()["id"] == str(deal_id)

    @patch("src.api.v1.routers.deals.DealService")
    async def test_get_not_found(self, mock_svc_cls: AsyncMock, client_owner: AsyncClient) -> None:
        """Non-existent deal returns 404."""
        from src.core.exceptions import NotFoundError

        deal_id = uuid.uuid4()
        mock_svc_cls.return_value.get_deal = AsyncMock(
            side_effect=NotFoundError("Deal", str(deal_id))
        )

        response = await client_owner.get(f"/api/v1/deals/{deal_id}")

        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Update deal
# ---------------------------------------------------------------------------


class TestUpdateDeal:
    """PUT /api/v1/deals/{deal_id}"""

    @patch("src.api.v1.routers.deals.DealService")
    async def test_update_success(self, mock_svc_cls: AsyncMock, client_owner: AsyncClient) -> None:
        """Owner can update a deal — returns 200."""
        deal_id = uuid.uuid4()
        updated = make_deal(deal_id=deal_id, title="Updated Deal", stage_id=_STAGE_ID)
        mock_svc_cls.return_value.update_deal = AsyncMock(return_value=updated)

        response = await client_owner.put(
            f"/api/v1/deals/{deal_id}", json={"title": "Updated Deal"}
        )

        assert response.status_code == 200
        assert response.json()["title"] == "Updated Deal"

    @patch("src.api.v1.routers.deals.DealService")
    async def test_update_not_found(
        self, mock_svc_cls: AsyncMock, client_owner: AsyncClient
    ) -> None:
        """Updating a non-existent deal returns 404."""
        from src.core.exceptions import NotFoundError

        deal_id = uuid.uuid4()
        mock_svc_cls.return_value.update_deal = AsyncMock(
            side_effect=NotFoundError("Deal", str(deal_id))
        )

        response = await client_owner.put(f"/api/v1/deals/{deal_id}", json={"title": "X"})

        assert response.status_code == 404

    @patch("src.api.v1.routers.deals.DealService")
    async def test_update_forbidden_rep(
        self, mock_svc_cls: AsyncMock, client_rep: AsyncClient
    ) -> None:
        """Sales rep cannot modify a deal not assigned to them — 403."""
        from src.core.exceptions import ForbiddenError

        deal_id = uuid.uuid4()
        mock_svc_cls.return_value.update_deal = AsyncMock(
            side_effect=ForbiddenError("Sales reps can only modify their assigned deals")
        )

        response = await client_rep.put(f"/api/v1/deals/{deal_id}", json={"title": "X"})

        assert response.status_code == 403


# ---------------------------------------------------------------------------
# Move deal stage
# ---------------------------------------------------------------------------


class TestMoveDealStage:
    """PUT /api/v1/deals/{deal_id}/stage"""

    @patch("src.api.v1.routers.deals.DealService")
    async def test_move_stage_success(
        self, mock_svc_cls: AsyncMock, client_owner: AsyncClient
    ) -> None:
        """Owner can move a deal to a new stage — returns 200."""
        deal_id = uuid.uuid4()
        new_stage_id = uuid.uuid4()
        deal = make_deal(deal_id=deal_id, stage_id=new_stage_id)
        mock_svc_cls.return_value.move_stage = AsyncMock(return_value=deal)

        response = await client_owner.put(
            f"/api/v1/deals/{deal_id}/stage",
            json={"stage_id": str(new_stage_id)},
        )

        assert response.status_code == 200
        assert response.json()["stageId"] == str(new_stage_id)

    @patch("src.api.v1.routers.deals.DealService")
    async def test_move_stage_not_found(
        self, mock_svc_cls: AsyncMock, client_owner: AsyncClient
    ) -> None:
        """Moving to a non-existent stage returns 404."""
        from src.core.exceptions import NotFoundError

        deal_id = uuid.uuid4()
        stage_id = uuid.uuid4()
        mock_svc_cls.return_value.move_stage = AsyncMock(
            side_effect=NotFoundError("PipelineStage", str(stage_id))
        )

        response = await client_owner.put(
            f"/api/v1/deals/{deal_id}/stage", json={"stage_id": str(stage_id)}
        )

        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Delete deal
# ---------------------------------------------------------------------------


class TestDeleteDeal:
    """DELETE /api/v1/deals/{deal_id}"""

    @patch("src.api.v1.routers.deals.DealService")
    async def test_delete_success(self, mock_svc_cls: AsyncMock, client_owner: AsyncClient) -> None:
        """Owner can delete a deal — returns 204."""
        deal_id = uuid.uuid4()
        mock_svc_cls.return_value.delete_deal = AsyncMock(return_value=None)

        response = await client_owner.delete(f"/api/v1/deals/{deal_id}")

        assert response.status_code == 204

    @patch("src.api.v1.routers.deals.DealService")
    async def test_delete_forbidden_rep(
        self, mock_svc_cls: AsyncMock, client_rep: AsyncClient
    ) -> None:
        """Sales rep cannot delete deals — 403."""
        from src.core.exceptions import ForbiddenError

        deal_id = uuid.uuid4()
        mock_svc_cls.return_value.delete_deal = AsyncMock(
            side_effect=ForbiddenError("Only owners and admins can delete deals")
        )

        response = await client_rep.delete(f"/api/v1/deals/{deal_id}")

        assert response.status_code == 403

    @patch("src.api.v1.routers.deals.DealService")
    async def test_delete_not_found(
        self, mock_svc_cls: AsyncMock, client_owner: AsyncClient
    ) -> None:
        """Deleting a non-existent deal returns 404."""
        from src.core.exceptions import NotFoundError

        deal_id = uuid.uuid4()
        mock_svc_cls.return_value.delete_deal = AsyncMock(
            side_effect=NotFoundError("Deal", str(deal_id))
        )

        response = await client_owner.delete(f"/api/v1/deals/{deal_id}")

        assert response.status_code == 404
