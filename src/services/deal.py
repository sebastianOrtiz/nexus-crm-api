"""
Deal service — manages sales opportunities and pipeline movements.
"""

import math
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from src.core.enums import UserRole
from src.core.exceptions import ForbiddenError, NotFoundError
from src.models.deal import Deal
from src.models.user import User
from src.repositories.deal import DealRepository
from src.repositories.pipeline_stage import PipelineStageRepository
from src.schemas.common import PaginatedResponse
from src.schemas.deal import DealCreate, DealMoveStage, DealResponse, DealUpdate


class DealService:
    """
    Business logic for deal management.

    Sales reps can only access deals assigned to them. Moving a deal to a
    won/lost stage automatically sets ``closed_at``.

    Args:
        session: Async database session.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._repo = DealRepository(session)
        self._stage_repo = PipelineStageRepository(session)

    def _assert_can_write(self, deal: Deal, current_user: User) -> None:
        """
        Raise ``ForbiddenError`` if the user may not modify this deal.

        Args:
            deal: The deal being modified.
            current_user: The requesting user.

        Raises:
            ForbiddenError: When the user lacks permission.
        """
        role = UserRole(current_user.role)
        if role == UserRole.VIEWER:
            raise ForbiddenError("Viewers have read-only access")
        if role == UserRole.SALES_REP and deal.assigned_to_id != current_user.id:
            raise ForbiddenError("Sales reps can only modify their assigned deals")

    async def list_deals(
        self,
        organization_id: UUID,
        current_user: User,
        *,
        stage_id: UUID | None = None,
        contact_id: UUID | None = None,
        company_id: UUID | None = None,
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> PaginatedResponse[DealResponse]:
        """
        Return a paginated, filterable list of deals.

        Args:
            organization_id: Tenant boundary UUID.
            current_user: The requesting user (sales reps see only theirs).
            stage_id: Optional filter by pipeline stage.
            contact_id: Optional filter by related contact.
            company_id: Optional filter by related company.
            page: 1-indexed page number.
            page_size: Records per page.

        Returns:
            Paginated response envelope.
        """
        page_size = min(page_size, MAX_PAGE_SIZE)
        offset = (page - 1) * page_size

        assigned_filter: UUID | None = None
        if UserRole(current_user.role) == UserRole.SALES_REP:
            assigned_filter = current_user.id

        deals, total = await self._repo.list_by_org(
            organization_id,
            stage_id=stage_id,
            assigned_to_id=assigned_filter,
            contact_id=contact_id,
            company_id=company_id,
            offset=offset,
            limit=page_size,
        )
        pages = math.ceil(total / page_size) if total else 1
        return PaginatedResponse(
            items=[DealResponse.model_validate(d) for d in deals],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )

    async def get_deal(self, deal_id: UUID, organization_id: UUID) -> Deal:
        """
        Fetch a deal by ID within a tenant.

        Args:
            deal_id: UUID of the target deal.
            organization_id: Tenant boundary UUID.

        Returns:
            The ``Deal`` ORM instance.

        Raises:
            NotFoundError: If not found.
        """
        deal = await self._repo.get_by_id_and_org(deal_id, organization_id)
        if deal is None:
            raise NotFoundError("Deal", str(deal_id))
        return deal

    async def create_deal(
        self,
        payload: DealCreate,
        organization_id: UUID,
        current_user: User,
    ) -> Deal:
        """
        Create a new deal in the pipeline.

        Args:
            payload: Validated creation data.
            organization_id: Tenant boundary UUID.
            current_user: The requesting user.

        Returns:
            The new ``Deal`` instance.

        Raises:
            ForbiddenError: If the user is a viewer.
            NotFoundError: If the target stage does not exist in the tenant.
        """
        if UserRole(current_user.role) == UserRole.VIEWER:
            raise ForbiddenError("Viewers cannot create deals")

        stage = await self._stage_repo.get_by_id_and_org(payload.stage_id, organization_id)
        if stage is None:
            raise NotFoundError("PipelineStage", str(payload.stage_id))

        data = payload.model_dump()
        if data.get("currency"):
            data["currency"] = data["currency"].value

        return await self._repo.create(organization_id=organization_id, **data)

    async def update_deal(
        self,
        deal_id: UUID,
        payload: DealUpdate,
        organization_id: UUID,
        current_user: User,
    ) -> Deal:
        """
        Apply a partial update to a deal.

        Args:
            deal_id: UUID of the deal to update.
            payload: Fields to change.
            organization_id: Tenant boundary UUID.
            current_user: The requesting user.

        Returns:
            The updated ``Deal`` instance.

        Raises:
            ForbiddenError: On permission violation.
            NotFoundError: If the deal or the new stage is not found.
        """
        deal = await self._repo.get_by_id_and_org(deal_id, organization_id)
        if deal is None:
            raise NotFoundError("Deal", str(deal_id))

        self._assert_can_write(deal, current_user)

        changes = payload.model_dump(exclude_none=True)

        if "stage_id" in changes:
            stage = await self._stage_repo.get_by_id_and_org(changes["stage_id"], organization_id)
            if stage is None:
                raise NotFoundError("PipelineStage", str(changes["stage_id"]))
            # Auto-set closed_at when moving to a terminal stage
            if (stage.is_won or stage.is_lost) and deal.closed_at is None:
                changes["closed_at"] = datetime.now(UTC)

        if "currency" in changes and changes["currency"] is not None:
            changes["currency"] = changes["currency"].value

        if not changes:
            return deal

        return await self._repo.update(deal, **changes)

    async def move_stage(
        self,
        deal_id: UUID,
        payload: DealMoveStage,
        organization_id: UUID,
        current_user: User,
    ) -> Deal:
        """
        Move a deal to a new pipeline stage.

        This is a convenience endpoint that wraps ``update_deal`` with only
        the ``stage_id`` change. Automatically closes the deal if the new
        stage is won or lost.

        Args:
            deal_id: UUID of the deal to move.
            payload: Contains the target ``stage_id``.
            organization_id: Tenant boundary UUID.
            current_user: The requesting user.

        Returns:
            The updated ``Deal`` instance.

        Raises:
            ForbiddenError: On permission violation.
            NotFoundError: If the deal or stage is not found.
        """
        return await self.update_deal(
            deal_id,
            DealUpdate(stage_id=payload.stage_id),
            organization_id,
            current_user,
        )

    async def delete_deal(
        self,
        deal_id: UUID,
        organization_id: UUID,
        current_user: User,
    ) -> None:
        """
        Delete a deal permanently.

        Args:
            deal_id: UUID of the deal to delete.
            organization_id: Tenant boundary UUID.
            current_user: The requesting user.

        Raises:
            ForbiddenError: If the user is not owner or admin.
            NotFoundError: If the deal is not found.
        """
        if UserRole(current_user.role) not in (UserRole.OWNER, UserRole.ADMIN):
            raise ForbiddenError("Only owners and admins can delete deals")

        deal = await self._repo.get_by_id_and_org(deal_id, organization_id)
        if deal is None:
            raise NotFoundError("Deal", str(deal_id))

        await self._repo.delete(deal)
