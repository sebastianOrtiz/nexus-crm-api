"""
Integration test fixtures — requieren una base de datos PostgreSQL activa.

Arquitectura de fixtures:
- ``create_test_tables`` (session-scope): crea/elimina tablas una vez por sesión.
- ``db_session`` (function-scope): sesión con rollback automático por test.
- ``client`` (function-scope): AsyncClient con la sesión de test inyectada.
- Fixtures de datos: ``org``, ``owner_user``, ``sales_rep_user``, tokens y headers.

El override de ``get_session`` garantiza que cada request HTTP del cliente de test
usa la misma sesión rolled-back, así ningún test contamina al siguiente.
"""

import os
from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from src.core.database import get_session
from src.core.enums import UserRole
from src.core.security import create_access_token, hash_password
from src.main import create_app
from src.models import Base
from src.models.organization import Organization
from src.models.user import User

# ---------------------------------------------------------------------------
# Test database
# ---------------------------------------------------------------------------

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/nexuscrm_test",
)

test_engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool, echo=False)

TestingSessionFactory = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


# ---------------------------------------------------------------------------
# Session-scoped: create schema + tables once
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="session")
async def create_test_tables() -> AsyncGenerator[None, None]:
    """
    Create the ``crm`` schema and all tables before the first test in the
    session, then drop everything after the last test.

    Yields:
        Nothing — used purely for setup/teardown side effects.
    """
    async with test_engine.begin() as conn:
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS crm"))
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.execute(text("DROP SCHEMA IF EXISTS crm CASCADE"))


# ---------------------------------------------------------------------------
# Function-scoped: fresh rolled-back session per test
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def db_session(create_test_tables: None) -> AsyncGenerator[AsyncSession, None]:
    """
    Provide a database session that is rolled back after each test.

    Uses a SAVEPOINT so the outer transaction boundary stays open between
    tests, giving near-zero per-test DB overhead.

    Args:
        create_test_tables: Ensures schema exists before this fixture runs.

    Yields:
        An ``AsyncSession`` that will be rolled back on cleanup.
    """
    async with TestingSessionFactory() as session:
        async with session.begin():
            yield session
            await session.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Provide an ``AsyncClient`` pointed at the FastAPI app with the test DB.

    The ``get_session`` dependency is overridden to yield the test session
    so every HTTP request inside a test uses the same rolled-back transaction.

    Args:
        db_session: The function-scoped test session.

    Yields:
        ``AsyncClient`` ready for HTTP requests.
    """
    app = create_app()

    async def _override_get_session() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_session] = _override_get_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# Data fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def org(db_session: AsyncSession) -> Organization:
    """
    Create and persist a test ``Organization``.

    Args:
        db_session: Injected test database session.

    Returns:
        Persisted ``Organization`` instance.
    """
    instance = Organization(
        name="Test Org",
        slug="test-org",
        plan="free",
        is_active=True,
    )
    db_session.add(instance)
    await db_session.flush()
    await db_session.refresh(instance)
    return instance


@pytest_asyncio.fixture
async def owner_user(db_session: AsyncSession, org: Organization) -> User:
    """
    Create and persist an ``owner`` user for the test organization.

    Args:
        db_session: Injected test database session.
        org: The test organization fixture.

    Returns:
        Persisted ``User`` with role ``owner``.
    """
    from datetime import UTC, datetime

    instance = User(
        organization_id=org.id,
        email="owner@test.com",
        password_hash=hash_password("Password1"),
        first_name="Test",
        last_name="Owner",
        role=UserRole.OWNER.value,
        is_active=True,
        created_at=datetime.now(UTC),
    )
    db_session.add(instance)
    await db_session.flush()
    await db_session.refresh(instance)
    return instance


@pytest_asyncio.fixture
async def sales_rep_user(db_session: AsyncSession, org: Organization) -> User:
    """
    Create and persist a ``sales_rep`` user for the test organization.

    Args:
        db_session: Injected test database session.
        org: The test organization fixture.

    Returns:
        Persisted ``User`` with role ``sales_rep``.
    """
    from datetime import UTC, datetime

    instance = User(
        organization_id=org.id,
        email="rep@test.com",
        password_hash=hash_password("Password1"),
        first_name="Test",
        last_name="Rep",
        role=UserRole.SALES_REP.value,
        is_active=True,
        created_at=datetime.now(UTC),
    )
    db_session.add(instance)
    await db_session.flush()
    await db_session.refresh(instance)
    return instance


@pytest_asyncio.fixture
def owner_token(owner_user: User) -> str:
    """
    Return a valid JWT access token for the owner user.

    Args:
        owner_user: The owner user fixture.

    Returns:
        Signed JWT string.
    """
    return create_access_token(owner_user.id, owner_user.organization_id, owner_user.role)


@pytest_asyncio.fixture
def sales_rep_token(sales_rep_user: User) -> str:
    """
    Return a valid JWT access token for the sales rep user.

    Args:
        sales_rep_user: The sales rep user fixture.

    Returns:
        Signed JWT string.
    """
    return create_access_token(
        sales_rep_user.id, sales_rep_user.organization_id, sales_rep_user.role
    )


@pytest_asyncio.fixture
def owner_headers(owner_token: str) -> dict[str, str]:
    """Authorization headers dict for the owner user."""
    return {"Authorization": f"Bearer {owner_token}"}


@pytest_asyncio.fixture
def rep_headers(sales_rep_token: str) -> dict[str, str]:
    """Authorization headers dict for the sales rep user."""
    return {"Authorization": f"Bearer {sales_rep_token}"}
