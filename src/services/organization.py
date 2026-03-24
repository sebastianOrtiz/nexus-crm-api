"""
Organization service — handles tenant-level operations.
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.enums import UserRole
from src.core.exceptions import ForbiddenError, NotFoundError
from src.models.organization import Organization
from src.models.user import User
from src.repositories.organization import OrganizationRepository
from src.schemas.organization import OrganizationUpdate


class OrganizationService:
    """
    Business logic for organization management.

    Only the ``owner`` role may mutate the organization record. These checks
    live here in the service, not in the router, so the permission logic
    stays framework-agnostic and testable.

    Args:
        session: Async database session.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._repo = OrganizationRepository(session)

    async def get(self, organization_id: UUID) -> Organization:
        """
        Retrieve the caller's organization.

        Args:
            organization_id: UUID of the tenant to fetch.

        Returns:
            The ``Organization`` ORM instance.

        Raises:
            NotFoundError: If the organization does not exist.
        """
        org = await self._repo.get_by_id(organization_id)
        if org is None:
            raise NotFoundError("Organization", str(organization_id))
        return org

    async def update(
        self,
        organization_id: UUID,
        payload: OrganizationUpdate,
        current_user: User,
    ) -> Organization:
        """
        Update mutable fields on the organization.

        Args:
            organization_id: UUID of the organization to modify.
            payload: Fields to update (all optional).
            current_user: The authenticated user requesting the change.

        Returns:
            The updated ``Organization`` instance.

        Raises:
            ForbiddenError: If the user is not the organization owner.
            NotFoundError: If the organization does not exist.
        """
        if UserRole(current_user.role) != UserRole.OWNER:
            raise ForbiddenError("Only the organization owner can modify organization settings")

        org = await self._repo.get_by_id(organization_id)
        if org is None:
            raise NotFoundError("Organization", str(organization_id))

        changes = payload.model_dump(exclude_none=True)
        if not changes:
            return org

        return await self._repo.update(org, **changes)
