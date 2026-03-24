"""
Deals router — CRUD plus stage-move endpoint.
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from src.api.v1.dependencies import CurrentUser, DBSession
from src.core.exceptions import ForbiddenError, NotFoundError
from src.schemas.common import PaginatedResponse
from src.schemas.deal import DealCreate, DealMoveStage, DealResponse, DealUpdate
from src.services.deal import DealService

router = APIRouter(prefix="/deals", tags=["deals"])


@router.get(
    "",
    response_model=PaginatedResponse[DealResponse],
    summary="List deals",
)
async def list_deals(
    current_user: CurrentUser,
    session: DBSession,
    stage_id: UUID | None = Query(default=None),
    contact_id: UUID | None = Query(default=None),
    company_id: UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[DealResponse]:
    """
    Return a paginated, filterable list of deals.

    Sales reps see only their assigned deals. Owners and admins see all.

    Args:
        current_user: Injected authenticated user.
        session: Injected async database session.
        stage_id: Optional filter by pipeline stage.
        contact_id: Optional filter by related contact.
        company_id: Optional filter by related company.
        page: Page number (1-indexed).
        page_size: Records per page.

    Returns:
        Paginated ``DealResponse`` list.
    """
    svc = DealService(session)
    return await svc.list_deals(
        current_user.organization_id,
        current_user,
        stage_id=stage_id,
        contact_id=contact_id,
        company_id=company_id,
        page=page,
        page_size=page_size,
    )


@router.post(
    "",
    response_model=DealResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a deal",
)
async def create_deal(
    payload: DealCreate,
    current_user: CurrentUser,
    session: DBSession,
) -> DealResponse:
    """
    Create a new deal in the pipeline.

    Args:
        payload: Deal creation data.
        current_user: Injected authenticated user.
        session: Injected async database session.

    Returns:
        The newly created ``DealResponse``.

    Raises:
        403 Forbidden: If the caller is a viewer.
        404 Not Found: If the specified stage does not exist in the tenant.
    """
    svc = DealService(session)
    try:
        deal = await svc.create_deal(payload, current_user.organization_id, current_user)
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return DealResponse.model_validate(deal)


@router.get(
    "/{deal_id}",
    response_model=DealResponse,
    summary="Get a deal by ID",
)
async def get_deal(deal_id: UUID, current_user: CurrentUser, session: DBSession) -> DealResponse:
    """
    Return a specific deal by ID.

    Args:
        deal_id: UUID of the target deal.
        current_user: Injected authenticated user.
        session: Injected async database session.

    Returns:
        ``DealResponse`` for the target deal.

    Raises:
        404 Not Found: If the deal is not found in the tenant.
    """
    svc = DealService(session)
    try:
        deal = await svc.get_deal(deal_id, current_user.organization_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return DealResponse.model_validate(deal)


@router.put(
    "/{deal_id}",
    response_model=DealResponse,
    summary="Update a deal",
)
async def update_deal(
    deal_id: UUID,
    payload: DealUpdate,
    current_user: CurrentUser,
    session: DBSession,
) -> DealResponse:
    """
    Apply a partial update to a deal.

    Args:
        deal_id: UUID of the deal to update.
        payload: Fields to change.
        current_user: Injected authenticated user.
        session: Injected async database session.

    Returns:
        Updated ``DealResponse``.

    Raises:
        403 Forbidden: On permission violation.
        404 Not Found: If the deal or new stage is not found.
    """
    svc = DealService(session)
    try:
        deal = await svc.update_deal(
            deal_id, payload, current_user.organization_id, current_user
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return DealResponse.model_validate(deal)


@router.put(
    "/{deal_id}/stage",
    response_model=DealResponse,
    summary="Move deal to a different stage",
)
async def move_deal_stage(
    deal_id: UUID,
    payload: DealMoveStage,
    current_user: CurrentUser,
    session: DBSession,
) -> DealResponse:
    """
    Move a deal to a new pipeline stage.

    Automatically sets ``closed_at`` if the target stage is won or lost.

    Args:
        deal_id: UUID of the deal to move.
        payload: The target stage ID.
        current_user: Injected authenticated user.
        session: Injected async database session.

    Returns:
        Updated ``DealResponse``.

    Raises:
        403 Forbidden: On permission violation.
        404 Not Found: If the deal or stage is not found.
    """
    svc = DealService(session)
    try:
        deal = await svc.move_stage(
            deal_id, payload, current_user.organization_id, current_user
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return DealResponse.model_validate(deal)


@router.delete(
    "/{deal_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a deal",
)
async def delete_deal(deal_id: UUID, current_user: CurrentUser, session: DBSession) -> None:
    """
    Permanently delete a deal.

    Args:
        deal_id: UUID of the deal to delete.
        current_user: Injected authenticated user.
        session: Injected async database session.

    Raises:
        403 Forbidden: If the caller is not owner or admin.
        404 Not Found: If the deal is not found.
    """
    svc = DealService(session)
    try:
        await svc.delete_deal(deal_id, current_user.organization_id, current_user)
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
