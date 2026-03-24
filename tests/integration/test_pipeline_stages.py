"""
Integration tests for pipeline stage management endpoints.

Tests cover:
- List stages (ordered, all authenticated users)
- Create stage (owner/admin success, sales rep/viewer forbidden)
- Update stage (owner/admin success, sales rep forbidden)
- Delete stage (owner success, sales rep forbidden, non-existent)
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.organization import Organization
from src.models.pipeline_stage import PipelineStage
from src.models.user import User


async def _make_stage(
    session: AsyncSession,
    org: Organization,
    *,
    name: str = "Prospect",
    order: int = 0,
    is_won: bool = False,
    is_lost: bool = False,
) -> PipelineStage:
    """Helper to persist a PipelineStage directly via the ORM."""
    stage = PipelineStage(
        organization_id=org.id,
        name=name,
        order=order,
        is_won=is_won,
        is_lost=is_lost,
    )
    session.add(stage)
    await session.flush()
    await session.refresh(stage)
    return stage


async def _make_viewer(
    session: AsyncSession, org: Organization, email: str = "stage.viewer@test.com"
) -> User:
    """Helper to create a viewer user."""
    from datetime import UTC, datetime

    from src.core.enums import UserRole
    from src.core.security import hash_password
    from src.models.user import User

    viewer = User(
        organization_id=org.id,
        email=email,
        password_hash=hash_password("Pass1"),
        first_name="View",
        last_name="Stage",
        role=UserRole.VIEWER.value,
        is_active=True,
        created_at=datetime.now(UTC),
    )
    session.add(viewer)
    await session.flush()
    await session.refresh(viewer)
    return viewer


@pytest.mark.asyncio
class TestListPipelineStages:
    """Tests for GET /api/v1/pipeline-stages."""

    async def test_returns_ordered_stages(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        org: Organization,
        owner_headers: dict,
    ) -> None:
        """Returns all stages for the organization ordered by the order field."""
        await _make_stage(db_session, org, name="Stage 1", order=0)
        await _make_stage(db_session, org, name="Stage 2", order=1)

        response = await client.get("/api/v1/pipeline-stages", headers=owner_headers)
        assert response.status_code == 200
        stages = response.json()
        assert len(stages) >= 2
        orders = [s["order"] for s in stages]
        assert orders == sorted(orders)

    async def test_list_requires_auth(self, client: AsyncClient) -> None:
        """Unauthenticated request returns 401."""
        response = await client.get("/api/v1/pipeline-stages")
        assert response.status_code == 401

    async def test_sales_rep_can_list_stages(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        org: Organization,
        rep_headers: dict,
    ) -> None:
        """Sales reps have read access to pipeline stages."""
        await _make_stage(db_session, org, name="Read Stage")
        response = await client.get("/api/v1/pipeline-stages", headers=rep_headers)
        assert response.status_code == 200


@pytest.mark.asyncio
class TestCreatePipelineStage:
    """Tests for POST /api/v1/pipeline-stages."""

    async def test_owner_can_create_stage(
        self,
        client: AsyncClient,
        owner_headers: dict,
    ) -> None:
        """Owner can create a pipeline stage."""
        response = await client.post(
            "/api/v1/pipeline-stages",
            headers=owner_headers,
            json={"name": "Qualified", "order": 1},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Qualified"
        assert "id" in data

    async def test_create_won_stage(
        self,
        client: AsyncClient,
        owner_headers: dict,
    ) -> None:
        """Owner can create a stage marked as won."""
        response = await client.post(
            "/api/v1/pipeline-stages",
            headers=owner_headers,
            json={"name": "Closed Won", "order": 10, "isWon": True},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["isWon"] is True

    async def test_sales_rep_cannot_create_stage(
        self,
        client: AsyncClient,
        rep_headers: dict,
    ) -> None:
        """Sales reps cannot create pipeline stages."""
        response = await client.post(
            "/api/v1/pipeline-stages",
            headers=rep_headers,
            json={"name": "Rep Stage"},
        )
        assert response.status_code == 403

    async def test_viewer_cannot_create_stage(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        org: Organization,
    ) -> None:
        """Viewers cannot create pipeline stages."""
        from src.core.security import create_access_token

        viewer = await _make_viewer(db_session, org, "ps.viewer@test.com")
        token = create_access_token(viewer.id, viewer.organization_id, viewer.role)
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.post(
            "/api/v1/pipeline-stages",
            headers=headers,
            json={"name": "Forbidden Stage"},
        )
        assert response.status_code == 403


@pytest.mark.asyncio
class TestUpdatePipelineStage:
    """Tests for PUT /api/v1/pipeline-stages/{id}."""

    async def test_owner_can_update_stage(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        org: Organization,
        owner_headers: dict,
    ) -> None:
        """Owner can update a pipeline stage."""
        stage = await _make_stage(db_session, org, name="Old Stage Name")
        response = await client.put(
            f"/api/v1/pipeline-stages/{stage.id}",
            headers=owner_headers,
            json={"name": "New Stage Name"},
        )
        assert response.status_code == 200
        assert response.json()["name"] == "New Stage Name"

    async def test_update_reorder_stage(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        org: Organization,
        owner_headers: dict,
    ) -> None:
        """Owner can change the order of a stage."""
        stage = await _make_stage(db_session, org, name="Reorder Me", order=5)
        response = await client.put(
            f"/api/v1/pipeline-stages/{stage.id}",
            headers=owner_headers,
            json={"order": 2},
        )
        assert response.status_code == 200
        assert response.json()["order"] == 2

    async def test_sales_rep_cannot_update_stage(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        org: Organization,
        rep_headers: dict,
    ) -> None:
        """Sales reps cannot update pipeline stages."""
        stage = await _make_stage(db_session, org, name="Rep Cannot Touch")
        response = await client.put(
            f"/api/v1/pipeline-stages/{stage.id}",
            headers=rep_headers,
            json={"name": "Hijacked"},
        )
        assert response.status_code == 403

    async def test_update_nonexistent_stage_returns_404(
        self,
        client: AsyncClient,
        owner_headers: dict,
    ) -> None:
        """Updating a non-existent stage returns 404."""
        response = await client.put(
            f"/api/v1/pipeline-stages/{uuid4()}",
            headers=owner_headers,
            json={"name": "Ghost Stage"},
        )
        assert response.status_code == 404


@pytest.mark.asyncio
class TestDeletePipelineStage:
    """Tests for DELETE /api/v1/pipeline-stages/{id}."""

    async def test_owner_can_delete_stage(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        org: Organization,
        owner_headers: dict,
    ) -> None:
        """Owner can delete a pipeline stage."""
        stage = await _make_stage(db_session, org, name="Deletable Stage")
        response = await client.delete(f"/api/v1/pipeline-stages/{stage.id}", headers=owner_headers)
        assert response.status_code == 204

    async def test_sales_rep_cannot_delete_stage(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        org: Organization,
        rep_headers: dict,
    ) -> None:
        """Sales reps cannot delete pipeline stages."""
        stage = await _make_stage(db_session, org, name="Rep Cannot Delete")
        response = await client.delete(f"/api/v1/pipeline-stages/{stage.id}", headers=rep_headers)
        assert response.status_code == 403

    async def test_delete_nonexistent_stage_returns_404(
        self,
        client: AsyncClient,
        owner_headers: dict,
    ) -> None:
        """Deleting a non-existent stage returns 404."""
        response = await client.delete(f"/api/v1/pipeline-stages/{uuid4()}", headers=owner_headers)
        assert response.status_code == 404
