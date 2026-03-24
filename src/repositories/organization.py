"""
Repository for Organization records.
"""

from sqlalchemy import select

from src.models.organization import Organization
from src.repositories.base import BaseRepository


class OrganizationRepository(BaseRepository[Organization]):
    """
    Data-access layer for ``Organization`` records.

    Inherits standard CRUD from ``BaseRepository``. Only organisation-specific
    queries (e.g., lookup by slug) are added here.
    """

    model = Organization

    async def get_by_slug(self, slug: str) -> Organization | None:
        """
        Find an organization by its URL-safe slug.

        Args:
            slug: The slug to search for.

        Returns:
            The matching organization or ``None``.
        """
        result = await self.session.execute(
            select(Organization).where(Organization.slug == slug)
        )
        return result.scalar_one_or_none()
