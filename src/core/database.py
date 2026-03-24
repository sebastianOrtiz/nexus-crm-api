"""
Async SQLAlchemy engine and session factory.

Design decisions:
- ``AsyncEngine`` + ``AsyncSession`` for non-blocking I/O throughout.
- ``expire_on_commit=False`` prevents lazy-load errors after a commit when
  the session is already closed (common in FastAPI dependency patterns).
- The ``get_session`` dependency yields a session and always closes it,
  even when an exception is raised in the route handler.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from src.core.config import settings


def _build_engine(database_url: str, *, testing: bool = False):  # type: ignore[no-untyped-def]
    """
    Create and return an ``AsyncEngine``.

    Args:
        database_url: Full async DSN, e.g.
            ``postgresql+asyncpg://user:pass@host/db``.
        testing: When ``True`` uses ``NullPool`` so every test gets a fresh
            connection without a shared pool — required for SQLite in-process
            test databases.

    Returns:
        Configured ``AsyncEngine`` instance.
    """
    kwargs: dict = {
        "echo": settings.DEBUG,
        "future": True,
    }
    if testing:
        kwargs["poolclass"] = NullPool

    return create_async_engine(str(database_url), **kwargs)


engine = _build_engine(str(settings.DATABASE_URL))

AsyncSessionFactory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields a database session per request.

    The session is committed automatically on success or rolled back and
    closed on any exception.

    Yields:
        An ``AsyncSession`` bound to the current request scope.
    """
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:  # noqa: BLE001 — intentionally broad: rollback on ANY error
            # We want to rollback for any exception type, not just SQLAlchemy
            # errors.  Application-level exceptions (e.g. validation errors
            # raised by a service) must also cause a rollback so the session
            # is never left in a dirty state.
            await session.rollback()
            raise
        finally:
            await session.close()
