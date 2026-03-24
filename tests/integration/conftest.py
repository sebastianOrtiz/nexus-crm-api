"""
Integration test fixtures — no database required.

All repository calls are mocked at the service layer.  The FastAPI
``get_current_user`` dependency is overridden to return a SimpleNamespace
object that mimics the User ORM model, so no real JWT decoding or database
lookup happens during tests.

Strategy
--------
* ``get_session`` is overridden to yield an ``AsyncMock`` — the session
  object is passed to repository constructors, but every repository method
  is patched before the request reaches it.
* ``get_current_user`` is overridden per-fixture to return users of different
  roles.  This avoids touching the JWT or UserRepository code paths.
* Helper factories (``make_*``) produce ``SimpleNamespace`` objects that
  satisfy Pydantic ``from_attributes=True`` validation used in response
  schemas.
"""

import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_current_user, get_session
from src.core.enums import UserRole
from src.core.security import create_access_token, create_refresh_token
from src.main import create_app

# ---------------------------------------------------------------------------
# Fixed UUIDs shared across tests (deterministic, not random)
# ---------------------------------------------------------------------------

ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
OWNER_ID = uuid.UUID("00000000-0000-0000-0000-000000000010")
ADMIN_ID = uuid.UUID("00000000-0000-0000-0000-000000000020")
REP_ID = uuid.UUID("00000000-0000-0000-0000-000000000030")
VIEWER_ID = uuid.UUID("00000000-0000-0000-0000-000000000040")


# ---------------------------------------------------------------------------
# SimpleNamespace factories — mimic ORM models with from_attributes=True
# ---------------------------------------------------------------------------


def make_org(
    *,
    org_id: uuid.UUID = ORG_ID,
    name: str = "Test Org",
    slug: str = "test-org",
) -> SimpleNamespace:
    """Return a SimpleNamespace that looks like an Organization ORM object."""
    return SimpleNamespace(
        id=org_id,
        name=name,
        slug=slug,
        plan="free",
        is_active=True,
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
    )


def make_user(
    *,
    user_id: uuid.UUID = OWNER_ID,
    org_id: uuid.UUID = ORG_ID,
    role: UserRole = UserRole.OWNER,
    email: str = "owner@test.com",
    is_active: bool = True,
) -> SimpleNamespace:
    """Return a SimpleNamespace that looks like a User ORM object."""
    return SimpleNamespace(
        id=user_id,
        organization_id=org_id,
        email=email,
        password_hash="$2b$12$fakehash",  # noqa: S106 — test fixture, not a real password
        first_name="Test",
        last_name=role.value.title(),
        role=role.value,
        is_active=is_active,
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
    )


def make_contact(
    *,
    contact_id: uuid.UUID | None = None,
    org_id: uuid.UUID = ORG_ID,
    first_name: str = "John",
    last_name: str = "Doe",
    email: str = "john.doe@test.com",
    assigned_to_id: uuid.UUID | None = None,
    source: str = "other",
) -> SimpleNamespace:
    """Return a SimpleNamespace that looks like a Contact ORM object."""
    now = datetime(2024, 1, 1, tzinfo=UTC)
    return SimpleNamespace(
        id=contact_id or uuid.uuid4(),
        organization_id=org_id,
        company_id=None,
        first_name=first_name,
        last_name=last_name,
        email=email,
        phone=None,
        position=None,
        source=source,
        notes=None,
        assigned_to_id=assigned_to_id,
        created_at=now,
        updated_at=now,
    )


def make_company(
    *,
    company_id: uuid.UUID | None = None,
    org_id: uuid.UUID = ORG_ID,
    name: str = "Acme Corp",
) -> SimpleNamespace:
    """Return a SimpleNamespace that looks like a Company ORM object."""
    now = datetime(2024, 1, 1, tzinfo=UTC)
    return SimpleNamespace(
        id=company_id or uuid.uuid4(),
        organization_id=org_id,
        name=name,
        domain="acme.com",
        industry="Technology",
        phone=None,
        address=None,
        notes=None,
        created_at=now,
        updated_at=now,
    )


def make_pipeline_stage(
    *,
    stage_id: uuid.UUID | None = None,
    org_id: uuid.UUID = ORG_ID,
    name: str = "Prospecting",
    order: int = 0,
    is_won: bool = False,
    is_lost: bool = False,
) -> SimpleNamespace:
    """Return a SimpleNamespace that looks like a PipelineStage ORM object."""
    return SimpleNamespace(
        id=stage_id or uuid.uuid4(),
        organization_id=org_id,
        name=name,
        order=order,
        is_won=is_won,
        is_lost=is_lost,
    )


def make_deal(
    *,
    deal_id: uuid.UUID | None = None,
    org_id: uuid.UUID = ORG_ID,
    stage_id: uuid.UUID | None = None,
    title: str = "Big Deal",
    value: float = 10000.0,
    currency: str = "USD",
    assigned_to_id: uuid.UUID | None = None,
    closed_at: datetime | None = None,
) -> SimpleNamespace:
    """Return a SimpleNamespace that looks like a Deal ORM object."""
    now = datetime(2024, 1, 1, tzinfo=UTC)
    return SimpleNamespace(
        id=deal_id or uuid.uuid4(),
        organization_id=org_id,
        title=title,
        value=value,
        currency=currency,
        stage_id=stage_id or uuid.uuid4(),
        contact_id=None,
        company_id=None,
        assigned_to_id=assigned_to_id,
        expected_close=None,
        closed_at=closed_at,
        created_at=now,
        updated_at=now,
    )


def make_activity(
    *,
    activity_id: uuid.UUID | None = None,
    org_id: uuid.UUID = ORG_ID,
    user_id: uuid.UUID = OWNER_ID,
    activity_type: str = "call",
    subject: str = "Follow-up call",
) -> SimpleNamespace:
    """Return a SimpleNamespace that looks like an Activity ORM object."""
    now = datetime(2024, 1, 1, tzinfo=UTC)
    return SimpleNamespace(
        id=activity_id or uuid.uuid4(),
        organization_id=org_id,
        type=activity_type,
        subject=subject,
        description=None,
        contact_id=None,
        deal_id=None,
        user_id=user_id,
        scheduled_at=None,
        completed_at=None,
        created_at=now,
    )


# ---------------------------------------------------------------------------
# Shared mock session override
# ---------------------------------------------------------------------------


async def _mock_session() -> AsyncGenerator[AsyncMock, None]:
    """Yield an AsyncMock in place of a real AsyncSession."""
    yield AsyncMock(spec=AsyncSession)


# ---------------------------------------------------------------------------
# App factory with mocked session
# ---------------------------------------------------------------------------


def _build_app():
    """Build a FastAPI app with the DB session dependency overridden."""
    app = create_app()
    app.dependency_overrides[get_session] = _mock_session
    return app


# ---------------------------------------------------------------------------
# Client fixtures — one per role
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def client_owner() -> AsyncGenerator[AsyncClient, None]:
    """AsyncClient authenticated as an OWNER user."""
    app = _build_app()
    user = make_user(user_id=OWNER_ID, org_id=ORG_ID, role=UserRole.OWNER)

    async def _current_user():
        return user

    app.dependency_overrides[get_current_user] = _current_user

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def client_admin() -> AsyncGenerator[AsyncClient, None]:
    """AsyncClient authenticated as an ADMIN user."""
    app = _build_app()
    user = make_user(user_id=ADMIN_ID, org_id=ORG_ID, role=UserRole.ADMIN, email="admin@test.com")

    async def _current_user():
        return user

    app.dependency_overrides[get_current_user] = _current_user

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def client_rep() -> AsyncGenerator[AsyncClient, None]:
    """AsyncClient authenticated as a SALES_REP user."""
    app = _build_app()
    user = make_user(user_id=REP_ID, org_id=ORG_ID, role=UserRole.SALES_REP, email="rep@test.com")

    async def _current_user():
        return user

    app.dependency_overrides[get_current_user] = _current_user

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def client_viewer() -> AsyncGenerator[AsyncClient, None]:
    """AsyncClient authenticated as a VIEWER user."""
    app = _build_app()
    user = make_user(
        user_id=VIEWER_ID, org_id=ORG_ID, role=UserRole.VIEWER, email="viewer@test.com"
    )

    async def _current_user():
        return user

    app.dependency_overrides[get_current_user] = _current_user

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def client_no_auth() -> AsyncGenerator[AsyncClient, None]:
    """AsyncClient with no auth override — real JWT validation applies (mocked session)."""
    app = _build_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# Token fixtures (for auth endpoint tests that handle tokens manually)
# ---------------------------------------------------------------------------


@pytest.fixture
def owner_token() -> str:
    """A valid access token for the owner user."""
    return create_access_token(OWNER_ID, ORG_ID, UserRole.OWNER.value)


@pytest.fixture
def owner_refresh_token() -> str:
    """A valid refresh token for the owner user."""
    return create_refresh_token(OWNER_ID, ORG_ID)
