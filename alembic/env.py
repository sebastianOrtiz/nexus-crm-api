"""
Alembic environment configuration.

Supports both offline (SQL script generation) and online (direct DB connection)
migration modes. Uses the async SQLAlchemy engine from ``src.core.database``
so migrations run through the same asyncpg driver as the application.
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# Import all models so Alembic can detect schema changes.
from src.models import Base  # noqa: F401 — side-effect import registers all tables
from src.core.config import settings

# ---------------------------------------------------------------------------
# Alembic Config
# ---------------------------------------------------------------------------
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Override the URL from settings so we never hard-code credentials.
config.set_main_option("sqlalchemy.url", str(settings.DATABASE_URL))

target_metadata = Base.metadata


# ---------------------------------------------------------------------------
# Offline mode
# ---------------------------------------------------------------------------

def run_migrations_offline() -> None:
    """
    Generate SQL migration scripts without connecting to the database.

    Useful for reviewing or applying migrations manually.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,
    )

    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Online mode
# ---------------------------------------------------------------------------

def do_run_migrations(connection: Connection) -> None:
    """
    Execute migrations using an active database connection.

    Args:
        connection: A synchronous SQLAlchemy connection supplied by the async
            wrapper.
    """
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_schemas=True,
        version_table_schema="crm",
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create the async engine and run migrations inside a sync wrapper."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Entry point for online migration mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
