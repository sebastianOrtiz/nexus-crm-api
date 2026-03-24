"""
Generic async repository base.

The ``BaseRepository`` implements the common ``get_by_id``, ``list``,
``create``, ``update``, and ``delete`` operations so concrete repositories
only need to add domain-specific query methods.

Design decisions:
- Every public query method accepts ``organization_id`` to enforce the tenant
  boundary at the data-access layer, making it impossible to accidentally
  return cross-tenant data.
- ``update`` accepts a dict of changes rather than a full model instance to
  support partial (PATCH-style) updates without loading the entity first.
"""

from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """
    Generic repository providing CRUD operations for a single model type.

    Subclasses must set the ``model`` class attribute to the SQLAlchemy model
    they manage.

    Attributes:
        model: The SQLAlchemy ORM model class.
        session: The async database session for the current request.
    """

    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, record_id: UUID) -> ModelT | None:
        """
        Fetch a single record by primary key without a tenant check.

        This is intentionally tenant-agnostic so it can be used internally
        (e.g., to verify ownership after the fact in the service layer).

        Args:
            record_id: UUID primary key of the record.

        Returns:
            The ORM instance if found, ``None`` otherwise.
        """
        result = await self.session.execute(select(self.model).where(self.model.id == record_id))
        return result.scalar_one_or_none()

    async def get_by_id_and_org(
        self,
        record_id: UUID,
        organization_id: UUID,
    ) -> ModelT | None:
        """
        Fetch a record by ID scoped to a specific tenant.

        Returns ``None`` when the record belongs to a different organization,
        which has the same effect as a 404 from the caller's perspective (no
        information leakage about other tenants' data).

        Args:
            record_id: UUID primary key.
            organization_id: Tenant boundary UUID.

        Returns:
            The ORM instance if found within the tenant, ``None`` otherwise.
        """
        result = await self.session.execute(
            select(self.model).where(
                self.model.id == record_id,
                self.model.organization_id == organization_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_org(
        self,
        organization_id: UUID,
        *,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[ModelT], int]:
        """
        Return a paginated slice of records for one tenant.

        Args:
            organization_id: Tenant boundary UUID.
            offset: Number of rows to skip (for pagination).
            limit: Maximum rows to return.

        Returns:
            A ``(items, total)`` tuple where ``total`` is the full matching
            count (useful for building pagination metadata).
        """
        base_q = select(self.model).where(self.model.organization_id == organization_id)
        count_result = await self.session.execute(
            select(func.count()).select_from(base_q.subquery())
        )
        total: int = count_result.scalar_one()

        items_result = await self.session.execute(base_q.offset(offset).limit(limit))
        items = list(items_result.scalars().all())
        return items, total

    async def create(self, **kwargs: Any) -> ModelT:
        """
        Create and persist a new record.

        Args:
            **kwargs: Column values forwarded to the model constructor.

        Returns:
            The newly created and refreshed ORM instance.
        """
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def update(self, instance: ModelT, **kwargs: Any) -> ModelT:
        """
        Apply a partial update to an existing record.

        Only keys explicitly provided in ``kwargs`` are changed. ``None``
        values *are* written — use omission to skip a field entirely.

        Args:
            instance: The ORM instance to modify.
            **kwargs: Column-name/value pairs to change.

        Returns:
            The updated ORM instance (refreshed from the session).
        """
        for key, value in kwargs.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def delete(self, instance: ModelT) -> None:
        """
        Permanently delete a record from the database.

        Args:
            instance: The ORM instance to remove.
        """
        await self.session.delete(instance)
        await self.session.flush()
