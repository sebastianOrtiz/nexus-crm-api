"""
Pipeline stages router — manage the ordered stages of the sales pipeline.
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from src.api.v1.dependencies import CurrentUser, DBSession
from src.core.exceptions import ForbiddenError, NotFoundError
from src.schemas.pipeline_stage import (
    PipelineStageCreate,
    PipelineStageResponse,
    PipelineStageUpdate,
)
from src.services.pipeline_stage import PipelineStageService

router = APIRouter(prefix="/pipeline-stages", tags=["pipeline-stages"])


@router.get(
    "",
    response_model=list[PipelineStageResponse],
    summary="List pipeline stages",
)
async def list_pipeline_stages(
    current_user: CurrentUser, session: DBSession
) -> list[PipelineStageResponse]:
    """
    Return all pipeline stages for the caller's organization, sorted by order.

    Args:
        current_user: Injected authenticated user.
        session: Injected async database session.

    Returns:
        Ordered list of ``PipelineStageResponse``.
    """
    svc = PipelineStageService(session)
    stages = await svc.list_stages(current_user.organization_id)
    return [PipelineStageResponse.model_validate(s) for s in stages]


@router.post(
    "",
    response_model=PipelineStageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a pipeline stage",
)
async def create_pipeline_stage(
    payload: PipelineStageCreate,
    current_user: CurrentUser,
    session: DBSession,
) -> PipelineStageResponse:
    """
    Create a new pipeline stage. Requires owner or admin role.

    Args:
        payload: Stage creation data.
        current_user: Injected authenticated user.
        session: Injected async database session.

    Returns:
        The newly created ``PipelineStageResponse``.

    Raises:
        403 Forbidden: If the caller is not owner or admin.
    """
    svc = PipelineStageService(session)
    try:
        stage = await svc.create_stage(payload, current_user.organization_id, current_user)
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    return PipelineStageResponse.model_validate(stage)


@router.put(
    "/{stage_id}",
    response_model=PipelineStageResponse,
    summary="Update a pipeline stage",
)
async def update_pipeline_stage(
    stage_id: UUID,
    payload: PipelineStageUpdate,
    current_user: CurrentUser,
    session: DBSession,
) -> PipelineStageResponse:
    """
    Apply a partial update to a pipeline stage.

    Args:
        stage_id: UUID of the stage to update.
        payload: Fields to change.
        current_user: Injected authenticated user.
        session: Injected async database session.

    Returns:
        Updated ``PipelineStageResponse``.

    Raises:
        403 Forbidden: On permission violation.
        404 Not Found: If the stage is not found.
    """
    svc = PipelineStageService(session)
    try:
        stage = await svc.update_stage(
            stage_id, payload, current_user.organization_id, current_user
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return PipelineStageResponse.model_validate(stage)


@router.delete(
    "/{stage_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a pipeline stage",
)
async def delete_pipeline_stage(
    stage_id: UUID,
    current_user: CurrentUser,
    session: DBSession,
) -> None:
    """
    Delete a pipeline stage.

    Will fail if any deals are currently in this stage (FK constraint).

    Args:
        stage_id: UUID of the stage to delete.
        current_user: Injected authenticated user.
        session: Injected async database session.

    Raises:
        403 Forbidden: On permission violation.
        404 Not Found: If the stage is not found.
    """
    svc = PipelineStageService(session)
    try:
        await svc.delete_stage(stage_id, current_user.organization_id, current_user)
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
