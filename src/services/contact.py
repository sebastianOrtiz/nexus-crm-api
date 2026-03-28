"""
Contact service — CRUD and permission checks for Contact records.

Sales reps can only update contacts assigned to them; owners and admins
have unrestricted access within the tenant.
"""

import math
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.helpers import clamp_page_size
from src.core.constants import DEFAULT_PAGE_SIZE
from src.core.enums import UserRole
from src.core.exceptions import ForbiddenError, NotFoundError
from src.models.contact import Contact
from src.models.user import User
from src.repositories.activity import ActivityRepository
from src.repositories.contact import ContactRepository
from src.schemas.activity import ActivityResponse
from src.schemas.common import PaginatedResponse
from src.schemas.contact import ContactCreate, ContactResponse, ContactUpdate


class ContactService:
    """
    Business logic for contact management.

    Args:
        session: Async database session.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._repo = ContactRepository(session)
        self._activity_repo = ActivityRepository(session)

    def _assert_can_write(self, contact: Contact, current_user: User) -> None:
        """
        Raise ``ForbiddenError`` if the user may not modify the given contact.

        Owners and admins can write any contact. Sales reps can only write
        contacts they are assigned to.

        Args:
            contact: The contact record being modified.
            current_user: The requesting user.

        Raises:
            ForbiddenError: When the user lacks permission.
        """
        role = UserRole(current_user.role)
        if role == UserRole.VIEWER:
            raise ForbiddenError("Viewers have read-only access")
        if role == UserRole.SALES_REP and contact.assigned_to_id != current_user.id:
            raise ForbiddenError("Sales reps can only modify their assigned contacts")

    async def list_contacts(
        self,
        organization_id: UUID,
        current_user: User,
        *,
        search: str | None = None,
        source: str | None = None,
        company_id: UUID | None = None,
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> PaginatedResponse[ContactResponse]:
        """
        Return a paginated, optionally filtered list of contacts.

        Sales reps see only their assigned contacts unless ``assigned_to_id``
        is not overridden.

        Args:
            organization_id: Tenant boundary UUID.
            current_user: The requesting user (drives scope filtering).
            search: Optional substring filter.
            company_id: Optional company filter.
            page: 1-indexed page number.
            page_size: Records per page.

        Returns:
            Paginated response envelope.
        """
        page_size = clamp_page_size(page_size)
        offset = (page - 1) * page_size

        assigned_filter: UUID | None = None
        if UserRole(current_user.role) == UserRole.SALES_REP:
            assigned_filter = current_user.id

        contacts, total = await self._repo.list_by_org(
            organization_id,
            search=search,
            source=source,
            company_id=company_id,
            assigned_to_id=assigned_filter,
            offset=offset,
            limit=page_size,
        )
        pages = math.ceil(total / page_size) if total else 1
        return PaginatedResponse(
            items=[ContactResponse.model_validate(c) for c in contacts],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )

    async def get_contact(self, contact_id: UUID, organization_id: UUID) -> Contact:
        """
        Fetch a contact by ID within a tenant.

        Args:
            contact_id: UUID of the target contact.
            organization_id: Tenant boundary UUID.

        Returns:
            The ``Contact`` ORM instance.

        Raises:
            NotFoundError: If not found.
        """
        contact = await self._repo.get_by_id_and_org(contact_id, organization_id)
        if contact is None:
            raise NotFoundError("Contact", str(contact_id))
        return contact

    async def create_contact(
        self,
        payload: ContactCreate,
        organization_id: UUID,
        current_user: User,
    ) -> Contact:
        """
        Create a new contact.

        Args:
            payload: Validated creation data.
            organization_id: Tenant boundary UUID.
            current_user: The requesting user.

        Returns:
            The new ``Contact`` instance.

        Raises:
            ForbiddenError: If the user is a viewer.
        """
        if UserRole(current_user.role) == UserRole.VIEWER:
            raise ForbiddenError("Viewers cannot create contacts")

        data = payload.model_dump()
        if data.get("source"):
            data["source"] = data["source"].value

        return await self._repo.create(organization_id=organization_id, **data)

    async def update_contact(
        self,
        contact_id: UUID,
        payload: ContactUpdate,
        organization_id: UUID,
        current_user: User,
    ) -> Contact:
        """
        Apply a partial update to a contact.

        Args:
            contact_id: UUID of the contact to update.
            payload: Fields to change.
            organization_id: Tenant boundary UUID.
            current_user: The requesting user.

        Returns:
            The updated ``Contact`` instance.

        Raises:
            ForbiddenError: On permission violation.
            NotFoundError: If not found.
        """
        contact = await self._repo.get_by_id_and_org(contact_id, organization_id)
        if contact is None:
            raise NotFoundError("Contact", str(contact_id))

        self._assert_can_write(contact, current_user)

        changes = payload.model_dump(exclude_none=True)
        if "source" in changes and changes["source"] is not None:
            changes["source"] = changes["source"].value

        if not changes:
            return contact

        return await self._repo.update(contact, **changes)

    async def delete_contact(
        self,
        contact_id: UUID,
        organization_id: UUID,
        current_user: User,
    ) -> None:
        """
        Delete a contact permanently.

        Args:
            contact_id: UUID of the contact to delete.
            organization_id: Tenant boundary UUID.
            current_user: The requesting user.

        Raises:
            ForbiddenError: If not owner or admin.
            NotFoundError: If not found.
        """
        if UserRole(current_user.role) not in (UserRole.OWNER, UserRole.ADMIN):
            raise ForbiddenError("Only owners and admins can delete contacts")

        contact = await self._repo.get_by_id_and_org(contact_id, organization_id)
        if contact is None:
            raise NotFoundError("Contact", str(contact_id))

        await self._repo.delete(contact)

    async def get_contact_activities(
        self, contact_id: UUID, organization_id: UUID
    ) -> list[ActivityResponse]:
        """
        Return all activities linked to a contact.

        Args:
            contact_id: UUID of the target contact.
            organization_id: Tenant boundary UUID.

        Returns:
            List of ``ActivityResponse`` schemas.

        Raises:
            NotFoundError: If the contact is not found.
        """
        contact = await self._repo.get_by_id_and_org(contact_id, organization_id)
        if contact is None:
            raise NotFoundError("Contact", str(contact_id))

        activities = await self._activity_repo.list_by_contact(contact_id, organization_id)
        return [ActivityResponse.model_validate(a) for a in activities]
