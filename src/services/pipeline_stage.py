"""
PipelineStage service — manages the ordered stages of a sales pipeline.
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.enums import UserRole
from src.core.exceptions import ForbiddenError, NotFoundError
from src.models.pipeline_stage import PipelineStage
from src.models.user import User
from src.repositories.pipeline_stage import PipelineStageRepository
from src.schemas.pipeline_stage import PipelineStageCreate, PipelineStageUpdate


class PipelineStageService:
    """
    Business logic for pipeline stage management.

    Only owners and admins may configure the pipeline.

    Args:
        session: Async database session.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._repo = PipelineStageRepository(session)

    def _assert_owner_or_admin(self, user: User) -> None:
        """
        Raise ``ForbiddenError`` if the user is not owner or admin.

        Args:
            user: The requesting user.

        Raises:
            ForbiddenError: When the user lacks the required role.
        """
        if UserRole(user.role) not in (UserRole.OWNER, UserRole.ADMIN):
            raise ForbiddenError("Only owners and admins can configure the pipeline")

    async def list_stages(self, organization_id: UUID) -> list[PipelineStage]:
        """
        Return all pipeline stages ordered by ``order`` column.

        Args:
            organization_id: Tenant boundary UUID.

        Returns:
            Ordered list of ``PipelineStage`` instances.
        """
        return await self._repo.list_by_org_ordered(organization_id)

    async def create_stage(
        self,
        payload: PipelineStageCreate,
        organization_id: UUID,
        current_user: User,
    ) -> PipelineStage:
        """
        Create a new pipeline stage.

        If ``order`` is not provided, the stage is appended at the end.

        Args:
            payload: Stage creation data.
            organization_id: Tenant boundary UUID.
            current_user: The requesting user.

        Returns:
            The newly created ``PipelineStage``.

        Raises:
            ForbiddenError: On permission violation.
        """
        self._assert_owner_or_admin(current_user)

        order = payload.order
        if order == 0:
            count = await self._repo.count_by_org(organization_id)
            order = count

        return await self._repo.create(
            organization_id=organization_id,
            name=payload.name,
            order=order,
            is_won=payload.is_won,
            is_lost=payload.is_lost,
        )

    async def update_stage(
        self,
        stage_id: UUID,
        payload: PipelineStageUpdate,
        organization_id: UUID,
        current_user: User,
    ) -> PipelineStage:
        """
        Apply a partial update to a pipeline stage.

        Args:
            stage_id: UUID of the stage to update.
            payload: Fields to change.
            organization_id: Tenant boundary UUID.
            current_user: The requesting user.

        Returns:
            The updated ``PipelineStage``.

        Raises:
            ForbiddenError: On permission violation.
            NotFoundError: If the stage is not found.
        """
        self._assert_owner_or_admin(current_user)

        stage = await self._repo.get_by_id_and_org(stage_id, organization_id)
        if stage is None:
            raise NotFoundError("PipelineStage", str(stage_id))

        changes = payload.model_dump(exclude_none=True)
        if not changes:
            return stage

        return await self._repo.update(stage, **changes)

    async def delete_stage(
        self,
        stage_id: UUID,
        organization_id: UUID,
        current_user: User,
    ) -> None:
        """
        Delete a pipeline stage.

        Note: The database enforces ``RESTRICT`` on the FK from ``Deal.stage_id``,
        so deletion will fail if any deals reference this stage.

        Args:
            stage_id: UUID of the stage to delete.
            organization_id: Tenant boundary UUID.
            current_user: The requesting user.

        Raises:
            ForbiddenError: On permission violation.
            NotFoundError: If the stage is not found.
        """
        self._assert_owner_or_admin(current_user)

        stage = await self._repo.get_by_id_and_org(stage_id, organization_id)
        if stage is None:
            raise NotFoundError("PipelineStage", str(stage_id))

        await self._repo.delete(stage)
