"""
Integration tests for deal CRUD endpoints.

Tests cover:
- List deals (pagination, owner vs sales rep scope)
- Create deal (success, forbidden for viewer, invalid stage)
- Get deal by ID
- Update deal (owner success, sales rep own vs other)
- Move deal to a different stage (stage movement, closed_at on won/lost)
- Delete deal (owner success, forbidden for sales rep)
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


async def _make_deal(
    session: AsyncSession,
    org: Organization,
    stage: PipelineStage,
    *,
    title: str = "Big Deal",
    assigned_to: User | None = None,
) -> "Deal":  # type: ignore[name-defined]  # noqa: F821
    """Helper to persist a Deal directly via the ORM."""
    from datetime import UTC, datetime

    from src.models.deal import Deal

    deal = Deal(
        organization_id=org.id,
        title=title,
        value=1000.0,
        currency="USD",
        stage_id=stage.id,
        assigned_to_id=assigned_to.id if assigned_to else None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    session.add(deal)
    await session.flush()
    await session.refresh(deal)
    return deal


@pytest.mark.asyncio
class TestListDeals:
    """Tests for GET /api/v1/deals."""

    async def test_list_returns_tenant_deals(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        org: Organization,
        owner_headers: dict,
    ) -> None:
        """Owner sees all deals in their organization."""
        stage = await _make_stage(db_session, org)
        await _make_deal(db_session, org, stage, title="Deal One")
        await _make_deal(db_session, org, stage, title="Deal Two")

        response = await client.get("/api/v1/deals", headers=owner_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 2

    async def test_sales_rep_sees_only_assigned_deals(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        org: Organization,
        sales_rep_user: User,
        rep_headers: dict,
    ) -> None:
        """Sales rep only sees deals assigned to them."""
        stage = await _make_stage(db_session, org)
        await _make_deal(db_session, org, stage, title="Assigned", assigned_to=sales_rep_user)
        await _make_deal(db_session, org, stage, title="Not Assigned")

        response = await client.get("/api/v1/deals", headers=rep_headers)
        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["assignedToId"] == str(sales_rep_user.id)

    async def test_list_requires_auth(self, client: AsyncClient) -> None:
        """Unauthenticated request returns 401."""
        response = await client.get("/api/v1/deals")
        assert response.status_code == 401

    async def test_list_pagination(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        org: Organization,
        owner_headers: dict,
    ) -> None:
        """Pagination metadata is correct."""
        stage = await _make_stage(db_session, org)
        for i in range(4):
            await _make_deal(db_session, org, stage, title=f"PageDeal{i}")

        response = await client.get(
            "/api/v1/deals",
            headers=owner_headers,
            params={"page": 1, "page_size": 2},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) <= 2
        assert data["page"] == 1
        assert data["pageSize"] == 2


@pytest.mark.asyncio
class TestCreateDeal:
    """Tests for POST /api/v1/deals."""

    async def test_owner_can_create_deal(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        org: Organization,
        owner_headers: dict,
    ) -> None:
        """Owner can create a deal."""
        stage = await _make_stage(db_session, org, name="Lead")
        response = await client.post(
            "/api/v1/deals",
            headers=owner_headers,
            json={"title": "New Deal", "stageId": str(stage.id), "value": 5000},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "New Deal"
        assert "id" in data

    async def test_create_with_invalid_stage_returns_404(
        self,
        client: AsyncClient,
        owner_headers: dict,
    ) -> None:
        """Creating a deal with a non-existent stage returns 404."""
        response = await client.post(
            "/api/v1/deals",
            headers=owner_headers,
            json={"title": "Ghost Deal", "stageId": str(uuid4())},
        )
        assert response.status_code == 404

    async def test_sales_rep_can_create_deal(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        org: Organization,
        rep_headers: dict,
    ) -> None:
        """Sales reps are allowed to create deals."""
        stage = await _make_stage(db_session, org, name="RepStage")
        response = await client.post(
            "/api/v1/deals",
            headers=rep_headers,
            json={"title": "Rep Deal", "stageId": str(stage.id)},
        )
        assert response.status_code == 201

    async def test_viewer_cannot_create_deal(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        org: Organization,
    ) -> None:
        """Viewers are forbidden from creating deals."""
        from datetime import UTC, datetime

        from src.core.enums import UserRole
        from src.core.security import create_access_token, hash_password
        from src.models.user import User

        stage = await _make_stage(db_session, org, name="ViewerStage")

        viewer = User(
            organization_id=org.id,
            email="deal.viewer@test.com",
            password_hash=hash_password("Pass1"),
            first_name="Viewer",
            last_name="Deal",
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
            "/api/v1/deals",
            headers=headers,
            json={"title": "Forbidden Deal", "stageId": str(stage.id)},
        )
        assert response.status_code == 403


@pytest.mark.asyncio
class TestGetDeal:
    """Tests for GET /api/v1/deals/{id}."""

    async def test_get_existing_deal(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        org: Organization,
        owner_headers: dict,
    ) -> None:
        """Returns 200 with deal details for an existing deal."""
        stage = await _make_stage(db_session, org)
        deal = await _make_deal(db_session, org, stage, title="Fetchable Deal")
        response = await client.get(f"/api/v1/deals/{deal.id}", headers=owner_headers)
        assert response.status_code == 200
        assert response.json()["id"] == str(deal.id)

    async def test_get_nonexistent_deal(
        self,
        client: AsyncClient,
        owner_headers: dict,
    ) -> None:
        """Returns 404 for a deal that does not exist."""
        response = await client.get(f"/api/v1/deals/{uuid4()}", headers=owner_headers)
        assert response.status_code == 404


@pytest.mark.asyncio
class TestUpdateDeal:
    """Tests for PUT /api/v1/deals/{id}."""

    async def test_owner_can_update_any_deal(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        org: Organization,
        owner_headers: dict,
    ) -> None:
        """Owner can update any deal."""
        stage = await _make_stage(db_session, org)
        deal = await _make_deal(db_session, org, stage, title="Old Title")
        response = await client.put(
            f"/api/v1/deals/{deal.id}",
            headers=owner_headers,
            json={"title": "New Title"},
        )
        assert response.status_code == 200
        assert response.json()["title"] == "New Title"

    async def test_sales_rep_cannot_update_unassigned_deal(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        org: Organization,
        rep_headers: dict,
    ) -> None:
        """Sales rep cannot update a deal not assigned to them."""
        stage = await _make_stage(db_session, org)
        deal = await _make_deal(db_session, org, stage, title="Not Mine")
        response = await client.put(
            f"/api/v1/deals/{deal.id}",
            headers=rep_headers,
            json={"title": "Hijacked"},
        )
        assert response.status_code == 403

    async def test_sales_rep_can_update_assigned_deal(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        org: Organization,
        sales_rep_user: User,
        rep_headers: dict,
    ) -> None:
        """Sales rep can update a deal assigned to them."""
        stage = await _make_stage(db_session, org)
        deal = await _make_deal(db_session, org, stage, title="My Deal", assigned_to=sales_rep_user)
        response = await client.put(
            f"/api/v1/deals/{deal.id}",
            headers=rep_headers,
            json={"title": "Updated My Deal"},
        )
        assert response.status_code == 200
        assert response.json()["title"] == "Updated My Deal"


@pytest.mark.asyncio
class TestMoveDealStage:
    """Tests for PUT /api/v1/deals/{id}/stage."""

    async def test_owner_can_move_deal_stage(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        org: Organization,
        owner_headers: dict,
    ) -> None:
        """Owner can move a deal to a different stage."""
        stage_a = await _make_stage(db_session, org, name="Stage A", order=0)
        stage_b = await _make_stage(db_session, org, name="Stage B", order=1)
        deal = await _make_deal(db_session, org, stage_a, title="Moving Deal")

        response = await client.put(
            f"/api/v1/deals/{deal.id}/stage",
            headers=owner_headers,
            json={"stageId": str(stage_b.id)},
        )
        assert response.status_code == 200
        assert response.json()["stageId"] == str(stage_b.id)

    async def test_move_to_won_stage_sets_closed_at(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        org: Organization,
        owner_headers: dict,
    ) -> None:
        """Moving a deal to a won stage automatically sets closed_at."""
        stage_open = await _make_stage(db_session, org, name="Open", order=0)
        stage_won = await _make_stage(db_session, org, name="Won", order=1, is_won=True)
        deal = await _make_deal(db_session, org, stage_open, title="About to Win")

        response = await client.put(
            f"/api/v1/deals/{deal.id}/stage",
            headers=owner_headers,
            json={"stageId": str(stage_won.id)},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["closedAt"] is not None

    async def test_move_to_nonexistent_stage_returns_404(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        org: Organization,
        owner_headers: dict,
    ) -> None:
        """Moving to a non-existent stage returns 404."""
        stage = await _make_stage(db_session, org)
        deal = await _make_deal(db_session, org, stage)

        response = await client.put(
            f"/api/v1/deals/{deal.id}/stage",
            headers=owner_headers,
            json={"stageId": str(uuid4())},
        )
        assert response.status_code == 404


@pytest.mark.asyncio
class TestDeleteDeal:
    """Tests for DELETE /api/v1/deals/{id}."""

    async def test_owner_can_delete_deal(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        org: Organization,
        owner_headers: dict,
    ) -> None:
        """Owner can delete any deal."""
        stage = await _make_stage(db_session, org)
        deal = await _make_deal(db_session, org, stage, title="To Delete")
        response = await client.delete(f"/api/v1/deals/{deal.id}", headers=owner_headers)
        assert response.status_code == 204

        get_response = await client.get(f"/api/v1/deals/{deal.id}", headers=owner_headers)
        assert get_response.status_code == 404

    async def test_sales_rep_cannot_delete_deal(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        org: Organization,
        sales_rep_user: User,
        rep_headers: dict,
    ) -> None:
        """Sales reps cannot delete deals even if assigned."""
        stage = await _make_stage(db_session, org)
        deal = await _make_deal(
            db_session, org, stage, title="My Protected Deal", assigned_to=sales_rep_user
        )
        response = await client.delete(f"/api/v1/deals/{deal.id}", headers=rep_headers)
        assert response.status_code == 403
