"""
Repository for Activity records.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select

from src.core.enums import ActivityType
from src.models.activity import Activity
from src.repositories.base import BaseRepository


class ActivityRepository(BaseRepository[Activity]):
    """Data-access layer for ``Activity`` records."""

    model = Activity

    async def list_by_org(
        self,
        organization_id: UUID,
        *,
        activity_type: ActivityType | None = None,
        contact_id: UUID | None = None,
        deal_id: UUID | None = None,
        user_id: UUID | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Activity], int]:
        """
        Paginated, filterable list of activities for one tenant.

        Args:
            organization_id: Tenant boundary UUID.
            activity_type: Optional filter by activity category.
            contact_id: Optional filter by related contact.
            deal_id: Optional filter by related deal.
            user_id: Optional filter by owner.
            from_date: Inclusive lower bound on ``scheduled_at``.
            to_date: Inclusive upper bound on ``scheduled_at``.
            offset: Rows to skip.
            limit: Maximum rows to return.

        Returns:
            ``(activities, total)`` tuple.
        """
        base_q = select(Activity).where(Activity.organization_id == organization_id)

        if activity_type is not None:
            base_q = base_q.where(Activity.type == activity_type.value)
        if contact_id is not None:
            base_q = base_q.where(Activity.contact_id == contact_id)
        if deal_id is not None:
            base_q = base_q.where(Activity.deal_id == deal_id)
        if user_id is not None:
            base_q = base_q.where(Activity.user_id == user_id)
        if from_date is not None:
            base_q = base_q.where(Activity.scheduled_at >= from_date)
        if to_date is not None:
            base_q = base_q.where(Activity.scheduled_at <= to_date)

        count_result = await self.session.execute(
            select(func.count()).select_from(base_q.subquery())
        )
        total: int = count_result.scalar_one()

        items_result = await self.session.execute(
            base_q.order_by(Activity.created_at.desc()).offset(offset).limit(limit)
        )
        return list(items_result.scalars().all()), total

    async def list_by_contact(
        self,
        contact_id: UUID,
        organization_id: UUID,
    ) -> list[Activity]:
        """
        Return all activities linked to a specific contact within a tenant.

        Args:
            contact_id: The contact FK to filter by.
            organization_id: Tenant boundary UUID.

        Returns:
            List of ``Activity`` instances ordered by creation date.
        """
        result = await self.session.execute(
            select(Activity).where(
                Activity.contact_id == contact_id,
                Activity.organization_id == organization_id,
            ).order_by(Activity.created_at.desc())
        )
        return list(result.scalars().all())

    async def count_this_week(self, organization_id: UUID, since: datetime) -> int:
        """
        Count activities created in the current week.

        Args:
            organization_id: Tenant boundary UUID.
            since: Start of the week (UTC datetime).

        Returns:
            Activity count.
        """
        result = await self.session.execute(
            select(func.count(Activity.id)).where(
                Activity.organization_id == organization_id,
                Activity.created_at >= since,
            )
        )
        return result.scalar_one()

    async def list_recent(self, organization_id: UUID, limit: int = 10) -> list[Activity]:
        """
        Return the most recent activities for the activity feed.

        Args:
            organization_id: Tenant boundary UUID.
            limit: Maximum number of activities to return.

        Returns:
            List of recent ``Activity`` instances.
        """
        result = await self.session.execute(
            select(Activity)
            .where(Activity.organization_id == organization_id)
            .order_by(Activity.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
