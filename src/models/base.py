"""
SQLAlchemy declarative base and shared column mixins.

All tables live in the ``crm`` schema so they are isolated from other
services that share the same PostgreSQL instance (events, search).
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from src.core.constants import DB_SCHEMA


class Base(DeclarativeBase):
    """
    Project-wide declarative base.

    All models inherit from this class. The ``__table_args__`` schema
    directive is applied per-model so Alembic targets the correct schema.
    """


class UUIDMixin:
    """
    Provides a UUID primary key column named ``id``.

    Using ``uuid.uuid4`` as the default ensures IDs are generated in Python
    (not in the DB), which makes unit tests that check IDs deterministic.
    """

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )


class TimestampMixin:
    """
    Provides ``created_at`` and ``updated_at`` audit columns.

    ``server_default`` and ``onupdate`` use DB-side functions so the values
    are set even when rows are inserted/updated outside the ORM.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


# Expose the schema name as a constant for use in __table_args__
SCHEMA = DB_SCHEMA
