"""
Repository for User records.
"""

from uuid import UUID

from sqlalchemy import func, select

from src.core.utils import normalize_email
from src.models.user import User
from src.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """
    Data-access layer for ``User`` records.

    All methods that accept ``organization_id`` enforce the tenant boundary
    so cross-org data leakage is structurally impossible.
    """

    model = User

    async def get_by_email(self, email: str) -> User | None:
        """
        Look up a user by e-mail address (case-insensitive).

        Used during login before we know the ``organization_id``.

        Args:
            email: The e-mail address to search for.

        Returns:
            The matching user or ``None``.
        """
        result = await self.session.execute(
            select(User).where(func.lower(User.email) == normalize_email(email))
        )
        return result.scalar_one_or_none()

    async def get_by_email_and_org(self, email: str, organization_id: UUID) -> User | None:
        """
        Look up a user by e-mail within a specific tenant.

        Args:
            email: The e-mail address to search for.
            organization_id: Tenant boundary UUID.

        Returns:
            The matching user or ``None``.
        """
        result = await self.session.execute(
            select(User).where(
                func.lower(User.email) == normalize_email(email),
                User.organization_id == organization_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_org(
        self,
        organization_id: UUID,
        *,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[User], int]:
        """
        Paginated list of all users in an organization.

        Args:
            organization_id: Tenant boundary UUID.
            offset: Rows to skip.
            limit: Maximum rows to return.

        Returns:
            ``(users, total)`` tuple.
        """
        base_q = select(User).where(User.organization_id == organization_id)
        count_result = await self.session.execute(
            select(func.count()).select_from(base_q.subquery())
        )
        total: int = count_result.scalar_one()

        items_result = await self.session.execute(base_q.offset(offset).limit(limit))
        return list(items_result.scalars().all()), total
