"""
Integration tests for pipeline stage management endpoints.

All repository calls are mocked — no PostgreSQL required.

Tests cover:
- GET  /api/v1/pipeline-stages              (list, all authenticated users)
- POST /api/v1/pipeline-stages              (owner/admin success, forbidden rep/viewer)
- PUT  /api/v1/pipeline-stages/{id}         (owner success, forbidden, 404)
- DELETE /api/v1/pipeline-stages/{id}       (owner success, forbidden, 404)
"""

import uuid
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient

from tests.integration.conftest import make_pipeline_stage

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_STAGE_PAYLOAD = {
    "name": "Prospecting",
    "order": 1,
    "is_won": False,
    "is_lost": False,
}


# ---------------------------------------------------------------------------
# List pipeline stages
# ---------------------------------------------------------------------------


class TestListPipelineStages:
    """GET /api/v1/pipeline-stages"""

    @patch("src.api.v1.routers.pipeline_stages.PipelineStageService")
    async def test_list_returns_200_for_owner(
        self, mock_svc_cls: AsyncMock, client_owner: AsyncClient
    ) -> None:
        """Owner sees all pipeline stages."""
        stage = make_pipeline_stage()
        mock_svc_cls.return_value.list_stages = AsyncMock(return_value=[stage])

        response = await client_owner.get("/api/v1/pipeline-stages")

        assert response.status_code == 200
        assert isinstance(response.json(), list)
        assert len(response.json()) == 1

    @patch("src.api.v1.routers.pipeline_stages.PipelineStageService")
    async def test_list_returns_200_for_viewer(
        self, mock_svc_cls: AsyncMock, client_viewer: AsyncClient
    ) -> None:
        """Viewer can also list pipeline stages (read-only access)."""
        mock_svc_cls.return_value.list_stages = AsyncMock(return_value=[])

        response = await client_viewer.get("/api/v1/pipeline-stages")

        assert response.status_code == 200

    async def test_list_unauthenticated(self, client_no_auth: AsyncClient) -> None:
        """Unauthenticated request returns 401."""
        response = await client_no_auth.get("/api/v1/pipeline-stages")
        assert response.status_code == 401

    @patch("src.api.v1.routers.pipeline_stages.PipelineStageService")
    async def test_list_preserves_order(
        self, mock_svc_cls: AsyncMock, client_owner: AsyncClient
    ) -> None:
        """Stages come back in their configured order."""
        stages = [
            make_pipeline_stage(name="Prospecting", order=0),
            make_pipeline_stage(name="Proposal", order=1),
            make_pipeline_stage(name="Closed Won", order=2, is_won=True),
        ]
        mock_svc_cls.return_value.list_stages = AsyncMock(return_value=stages)

        response = await client_owner.get("/api/v1/pipeline-stages")

        assert response.status_code == 200
        items = response.json()
        assert len(items) == 3
        assert items[0]["name"] == "Prospecting"
        assert items[2]["isWon"] is True


# ---------------------------------------------------------------------------
# Create pipeline stage
# ---------------------------------------------------------------------------


class TestCreatePipelineStage:
    """POST /api/v1/pipeline-stages"""

    @patch("src.api.v1.routers.pipeline_stages.PipelineStageService")
    async def test_create_success_owner(
        self, mock_svc_cls: AsyncMock, client_owner: AsyncClient
    ) -> None:
        """Owner can create a pipeline stage — returns 201."""
        stage = make_pipeline_stage(name="Prospecting")
        mock_svc_cls.return_value.create_stage = AsyncMock(return_value=stage)

        response = await client_owner.post("/api/v1/pipeline-stages", json=_STAGE_PAYLOAD)

        assert response.status_code == 201
        assert response.json()["name"] == "Prospecting"

    @patch("src.api.v1.routers.pipeline_stages.PipelineStageService")
    async def test_create_success_admin(
        self, mock_svc_cls: AsyncMock, client_admin: AsyncClient
    ) -> None:
        """Admin can create a pipeline stage."""
        stage = make_pipeline_stage(name="Prospecting")
        mock_svc_cls.return_value.create_stage = AsyncMock(return_value=stage)

        response = await client_admin.post("/api/v1/pipeline-stages", json=_STAGE_PAYLOAD)

        assert response.status_code == 201

    @patch("src.api.v1.routers.pipeline_stages.PipelineStageService")
    async def test_create_forbidden_rep(
        self, mock_svc_cls: AsyncMock, client_rep: AsyncClient
    ) -> None:
        """Sales rep cannot create pipeline stages — 403."""
        from src.core.exceptions import ForbiddenError

        mock_svc_cls.return_value.create_stage = AsyncMock(
            side_effect=ForbiddenError("Only owners and admins can configure the pipeline")
        )

        response = await client_rep.post("/api/v1/pipeline-stages", json=_STAGE_PAYLOAD)

        assert response.status_code == 403

    @patch("src.api.v1.routers.pipeline_stages.PipelineStageService")
    async def test_create_forbidden_viewer(
        self, mock_svc_cls: AsyncMock, client_viewer: AsyncClient
    ) -> None:
        """Viewer cannot create pipeline stages — 403."""
        from src.core.exceptions import ForbiddenError

        mock_svc_cls.return_value.create_stage = AsyncMock(
            side_effect=ForbiddenError("Only owners and admins can configure the pipeline")
        )

        response = await client_viewer.post("/api/v1/pipeline-stages", json=_STAGE_PAYLOAD)

        assert response.status_code == 403

    async def test_create_missing_name(self, client_owner: AsyncClient) -> None:
        """Missing required 'name' field returns 422."""
        response = await client_owner.post("/api/v1/pipeline-stages", json={"order": 1})
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Update pipeline stage
# ---------------------------------------------------------------------------


class TestUpdatePipelineStage:
    """PUT /api/v1/pipeline-stages/{stage_id}"""

    @patch("src.api.v1.routers.pipeline_stages.PipelineStageService")
    async def test_update_success(self, mock_svc_cls: AsyncMock, client_owner: AsyncClient) -> None:
        """Owner can update a pipeline stage — returns 200."""
        stage_id = uuid.uuid4()
        updated = make_pipeline_stage(stage_id=stage_id, name="Negotiation")
        mock_svc_cls.return_value.update_stage = AsyncMock(return_value=updated)

        response = await client_owner.put(
            f"/api/v1/pipeline-stages/{stage_id}",
            json={"name": "Negotiation"},
        )

        assert response.status_code == 200
        assert response.json()["name"] == "Negotiation"

    @patch("src.api.v1.routers.pipeline_stages.PipelineStageService")
    async def test_update_not_found(
        self, mock_svc_cls: AsyncMock, client_owner: AsyncClient
    ) -> None:
        """Updating a non-existent stage returns 404."""
        from src.core.exceptions import NotFoundError

        stage_id = uuid.uuid4()
        mock_svc_cls.return_value.update_stage = AsyncMock(
            side_effect=NotFoundError("PipelineStage", str(stage_id))
        )

        response = await client_owner.put(f"/api/v1/pipeline-stages/{stage_id}", json={"name": "X"})

        assert response.status_code == 404

    @patch("src.api.v1.routers.pipeline_stages.PipelineStageService")
    async def test_update_forbidden_rep(
        self, mock_svc_cls: AsyncMock, client_rep: AsyncClient
    ) -> None:
        """Sales rep cannot update pipeline stages — 403."""
        from src.core.exceptions import ForbiddenError

        stage_id = uuid.uuid4()
        mock_svc_cls.return_value.update_stage = AsyncMock(
            side_effect=ForbiddenError("Only owners and admins can configure the pipeline")
        )

        response = await client_rep.put(f"/api/v1/pipeline-stages/{stage_id}", json={"name": "X"})

        assert response.status_code == 403


# ---------------------------------------------------------------------------
# Delete pipeline stage
# ---------------------------------------------------------------------------


class TestDeletePipelineStage:
    """DELETE /api/v1/pipeline-stages/{stage_id}"""

    @patch("src.api.v1.routers.pipeline_stages.PipelineStageService")
    async def test_delete_success(self, mock_svc_cls: AsyncMock, client_owner: AsyncClient) -> None:
        """Owner can delete a pipeline stage — returns 204."""
        stage_id = uuid.uuid4()
        mock_svc_cls.return_value.delete_stage = AsyncMock(return_value=None)

        response = await client_owner.delete(f"/api/v1/pipeline-stages/{stage_id}")

        assert response.status_code == 204

    @patch("src.api.v1.routers.pipeline_stages.PipelineStageService")
    async def test_delete_forbidden_rep(
        self, mock_svc_cls: AsyncMock, client_rep: AsyncClient
    ) -> None:
        """Sales rep cannot delete pipeline stages — 403."""
        from src.core.exceptions import ForbiddenError

        stage_id = uuid.uuid4()
        mock_svc_cls.return_value.delete_stage = AsyncMock(
            side_effect=ForbiddenError("Only owners and admins can configure the pipeline")
        )

        response = await client_rep.delete(f"/api/v1/pipeline-stages/{stage_id}")

        assert response.status_code == 403

    @patch("src.api.v1.routers.pipeline_stages.PipelineStageService")
    async def test_delete_not_found(
        self, mock_svc_cls: AsyncMock, client_owner: AsyncClient
    ) -> None:
        """Deleting a non-existent stage returns 404."""
        from src.core.exceptions import NotFoundError

        stage_id = uuid.uuid4()
        mock_svc_cls.return_value.delete_stage = AsyncMock(
            side_effect=NotFoundError("PipelineStage", str(stage_id))
        )

        response = await client_owner.delete(f"/api/v1/pipeline-stages/{stage_id}")

        assert response.status_code == 404
