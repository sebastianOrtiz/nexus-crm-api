"""
Activity service — manages CRM activities (calls, emails, meetings, notes).
"""

import math
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from src.core.enums import ActivityType, UserRole
from src.core.exceptions import ForbiddenError, NotFoundError
from src.models.activity import Activity
from src.models.user import User
from src.repositories.activity import ActivityRepository
from src.schemas.activity import ActivityCreate, ActivityResponse, ActivityUpdate
from src.schemas.common import PaginatedResponse


class ActivityService:
    """
    Business logic for activity management.

    Sales reps can only modify their own activities. All other roles have
    full access within the tenant.

    Args:
        session: Async database session.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._repo = ActivityRepository(session)

    def _assert_can_write(self, activity: Activity, current_user: User) -> None:
        """
        Raise ``ForbiddenError`` if the user may not modify this activity.

        Args:
            activity: The activity being modified.
            current_user: The requesting user.

        Raises:
            ForbiddenError: When the user lacks permission.
        """
        role = UserRole(current_user.role)
        if role == UserRole.VIEWER:
            raise ForbiddenError("Viewers have read-only access")
        if role == UserRole.SALES_REP and activity.user_id != current_user.id:
            raise ForbiddenError("Sales reps can only modify their own activities")

    async def list_activities(
        self,
        organization_id: UUID,
        current_user: User,
        *,
        activity_type: ActivityType | None = None,
        contact_id: UUID | None = None,
        deal_id: UUID | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> PaginatedResponse[ActivityResponse]:
        """
        Return a paginated, filterable list of activities.

        Args:
            organization_id: Tenant boundary UUID.
            current_user: The requesting user.
            activity_type: Optional type filter.
            contact_id: Optional contact filter.
            deal_id: Optional deal filter.
            from_date: Inclusive lower bound on ``scheduled_at``.
            to_date: Inclusive upper bound on ``scheduled_at``.
            page: 1-indexed page number.
            page_size: Records per page.

        Returns:
            Paginated response envelope.
        """
        page_size = min(page_size, MAX_PAGE_SIZE)
        offset = (page - 1) * page_size

        user_filter: UUID | None = None
        if UserRole(current_user.role) == UserRole.SALES_REP:
            user_filter = current_user.id

        activities, total = await self._repo.list_by_org(
            organization_id,
            activity_type=activity_type,
            contact_id=contact_id,
            deal_id=deal_id,
            user_id=user_filter,
            from_date=from_date,
            to_date=to_date,
            offset=offset,
            limit=page_size,
        )
        pages = math.ceil(total / page_size) if total else 1
        return PaginatedResponse(
            items=[ActivityResponse.model_validate(a) for a in activities],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )

    async def get_activity(self, activity_id: UUID, organization_id: UUID) -> Activity:
        """
        Fetch an activity by ID within a tenant.

        Args:
            activity_id: UUID of the target activity.
            organization_id: Tenant boundary UUID.

        Returns:
            The ``Activity`` ORM instance.

        Raises:
            NotFoundError: If not found.
        """
        activity = await self._repo.get_by_id_and_org(activity_id, organization_id)
        if activity is None:
            raise NotFoundError("Activity", str(activity_id))
        return activity

    async def create_activity(
        self,
        payload: ActivityCreate,
        organization_id: UUID,
        current_user: User,
    ) -> Activity:
        """
        Create a new activity owned by the current user.

        Args:
            payload: Validated creation data.
            organization_id: Tenant boundary UUID.
            current_user: The user who owns the activity.

        Returns:
            The new ``Activity`` instance.

        Raises:
            ForbiddenError: If the user is a viewer.
        """
        if UserRole(current_user.role) == UserRole.VIEWER:
            raise ForbiddenError("Viewers cannot create activities")

        data = payload.model_dump()
        data["type"] = data["type"].value

        return await self._repo.create(
            organization_id=organization_id,
            user_id=current_user.id,
            created_at=datetime.now(UTC),
            **data,
        )

    async def update_activity(
        self,
        activity_id: UUID,
        payload: ActivityUpdate,
        organization_id: UUID,
        current_user: User,
    ) -> Activity:
        """
        Apply a partial update to an activity.

        Args:
            activity_id: UUID of the activity to update.
            payload: Fields to change.
            organization_id: Tenant boundary UUID.
            current_user: The requesting user.

        Returns:
            The updated ``Activity`` instance.

        Raises:
            ForbiddenError: On permission violation.
            NotFoundError: If not found.
        """
        activity = await self._repo.get_by_id_and_org(activity_id, organization_id)
        if activity is None:
            raise NotFoundError("Activity", str(activity_id))

        self._assert_can_write(activity, current_user)

        changes = payload.model_dump(exclude_none=True)
        if "type" in changes and changes["type"] is not None:
            changes["type"] = changes["type"].value

        if not changes:
            return activity

        return await self._repo.update(activity, **changes)

    async def delete_activity(
        self,
        activity_id: UUID,
        organization_id: UUID,
        current_user: User,
    ) -> None:
        """
        Delete an activity permanently.

        Args:
            activity_id: UUID of the activity to delete.
            organization_id: Tenant boundary UUID.
            current_user: The requesting user.

        Raises:
            ForbiddenError: On permission violation.
            NotFoundError: If not found.
        """
        activity = await self._repo.get_by_id_and_org(activity_id, organization_id)
        if activity is None:
            raise NotFoundError("Activity", str(activity_id))

        self._assert_can_write(activity, current_user)
        await self._repo.delete(activity)
