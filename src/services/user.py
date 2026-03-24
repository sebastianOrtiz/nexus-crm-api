"""
User service — manages users within an organization.
"""

import math
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from src.core.enums import UserRole
from src.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from src.core.security import hash_password
from src.models.user import User
from src.repositories.user import UserRepository
from src.schemas.common import PaginatedResponse
from src.schemas.user import UserCreate, UserResponse, UserUpdate


class UserService:
    """
    Business logic for user management within a tenant.

    Args:
        session: Async database session.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._repo = UserRepository(session)

    async def list_users(
        self,
        organization_id: UUID,
        *,
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> PaginatedResponse[UserResponse]:
        """
        Return a paginated list of users in the caller's organization.

        Args:
            organization_id: Tenant boundary UUID.
            page: 1-indexed page number.
            page_size: Records per page (capped at MAX_PAGE_SIZE).

        Returns:
            Paginated response envelope with ``UserResponse`` items.
        """
        page_size = min(page_size, MAX_PAGE_SIZE)
        offset = (page - 1) * page_size

        users, total = await self._repo.list_by_org(
            organization_id, offset=offset, limit=page_size
        )
        pages = math.ceil(total / page_size) if total else 1
        return PaginatedResponse(
            items=[UserResponse.model_validate(u) for u in users],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )

    async def get_user(self, user_id: UUID, organization_id: UUID) -> User:
        """
        Fetch a user by ID within a tenant.

        Args:
            user_id: UUID of the target user.
            organization_id: Tenant boundary UUID.

        Returns:
            The ``User`` ORM instance.

        Raises:
            NotFoundError: If the user does not exist in the tenant.
        """
        user = await self._repo.get_by_id_and_org(user_id, organization_id)
        if user is None:
            raise NotFoundError("User", str(user_id))
        return user

    async def create_user(
        self,
        payload: UserCreate,
        organization_id: UUID,
        current_user: User,
    ) -> User:
        """
        Invite/create a new user in the organization.

        Args:
            payload: Validated user creation data.
            organization_id: Tenant boundary UUID.
            current_user: The authenticated user requesting the creation.

        Returns:
            The newly created ``User`` instance.

        Raises:
            ForbiddenError: If the caller is not owner or admin.
            ConflictError: If the e-mail is already registered.
        """
        if UserRole(current_user.role) not in (UserRole.OWNER, UserRole.ADMIN):
            raise ForbiddenError("Only owners and admins can add users")

        existing = await self._repo.get_by_email(payload.email.lower())
        if existing is not None:
            raise ConflictError(f"Email '{payload.email}' is already registered")

        return await self._repo.create(
            organization_id=organization_id,
            email=payload.email.lower(),
            password_hash=hash_password(payload.password),
            first_name=payload.first_name,
            last_name=payload.last_name,
            role=payload.role.value,
            is_active=True,
            created_at=datetime.now(UTC),
        )

    async def update_user(
        self,
        user_id: UUID,
        payload: UserUpdate,
        organization_id: UUID,
        current_user: User,
    ) -> User:
        """
        Update a user's profile or role.

        Rules:
        - Owners can update anyone.
        - Admins can update non-owners.
        - A user cannot demote themselves.

        Args:
            user_id: UUID of the user to update.
            payload: Partial update data.
            organization_id: Tenant boundary UUID.
            current_user: The authenticated user requesting the change.

        Returns:
            The updated ``User`` instance.

        Raises:
            ForbiddenError: On permission violations.
            NotFoundError: If the target user is not found.
        """
        if UserRole(current_user.role) not in (UserRole.OWNER, UserRole.ADMIN):
            raise ForbiddenError("Only owners and admins can update users")

        target = await self._repo.get_by_id_and_org(user_id, organization_id)
        if target is None:
            raise NotFoundError("User", str(user_id))

        # Admins cannot modify owners
        if (
            UserRole(current_user.role) == UserRole.ADMIN
            and UserRole(target.role) == UserRole.OWNER
        ):
            raise ForbiddenError("Admins cannot modify the organization owner")

        changes = payload.model_dump(exclude_none=True)
        if "role" in changes:
            changes["role"] = changes["role"].value

        return await self._repo.update(target, **changes)

    async def delete_user(
        self,
        user_id: UUID,
        organization_id: UUID,
        current_user: User,
    ) -> None:
        """
        Soft-deactivate a user (set ``is_active=False``).

        The owner cannot deactivate themselves.

        Args:
            user_id: UUID of the user to deactivate.
            organization_id: Tenant boundary UUID.
            current_user: The authenticated user requesting the action.

        Raises:
            ForbiddenError: On permission violations.
            NotFoundError: If the target user is not found.
        """
        if UserRole(current_user.role) not in (UserRole.OWNER, UserRole.ADMIN):
            raise ForbiddenError("Only owners and admins can deactivate users")

        target = await self._repo.get_by_id_and_org(user_id, organization_id)
        if target is None:
            raise NotFoundError("User", str(user_id))

        if target.id == current_user.id:
            raise ForbiddenError("You cannot deactivate your own account")

        if (
            UserRole(current_user.role) == UserRole.ADMIN
            and UserRole(target.role) == UserRole.OWNER
        ):
            raise ForbiddenError("Admins cannot deactivate the organization owner")

        await self._repo.update(target, is_active=False)
