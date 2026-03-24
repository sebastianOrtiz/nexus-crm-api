"""
Activities router — full CRUD with filtering.
"""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from src.api.v1.dependencies import CurrentUser, DBSession
from src.core.enums import ActivityType
from src.core.exceptions import ForbiddenError, NotFoundError
from src.schemas.activity import ActivityCreate, ActivityResponse, ActivityUpdate
from src.schemas.common import PaginatedResponse
from src.services.activity import ActivityService

router = APIRouter(prefix="/activities", tags=["activities"])


@router.get(
    "",
    response_model=PaginatedResponse[ActivityResponse],
    summary="List activities",
)
async def list_activities(
    current_user: CurrentUser,
    session: DBSession,
    activity_type: ActivityType | None = Query(default=None),
    contact_id: UUID | None = Query(default=None),
    deal_id: UUID | None = Query(default=None),
    from_date: datetime | None = Query(default=None),
    to_date: datetime | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[ActivityResponse]:
    """
    Return a paginated, filterable list of activities.

    Sales reps see only their own activities. Owners and admins see all.

    Args:
        current_user: Injected authenticated user.
        session: Injected async database session.
        activity_type: Optional type filter (call, email, meeting, note).
        contact_id: Optional filter by related contact.
        deal_id: Optional filter by related deal.
        from_date: Inclusive lower bound on ``scheduled_at``.
        to_date: Inclusive upper bound on ``scheduled_at``.
        page: Page number (1-indexed).
        page_size: Records per page.

    Returns:
        Paginated ``ActivityResponse`` list.
    """
    svc = ActivityService(session)
    return await svc.list_activities(
        current_user.organization_id,
        current_user,
        activity_type=activity_type,
        contact_id=contact_id,
        deal_id=deal_id,
        from_date=from_date,
        to_date=to_date,
        page=page,
        page_size=page_size,
    )


@router.post(
    "",
    response_model=ActivityResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an activity",
)
async def create_activity(
    payload: ActivityCreate,
    current_user: CurrentUser,
    session: DBSession,
) -> ActivityResponse:
    """
    Log a new activity.

    Args:
        payload: Activity creation data.
        current_user: Injected authenticated user.
        session: Injected async database session.

    Returns:
        The newly created ``ActivityResponse``.

    Raises:
        403 Forbidden: If the caller is a viewer.
    """
    svc = ActivityService(session)
    try:
        activity = await svc.create_activity(payload, current_user.organization_id, current_user)
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    return ActivityResponse.model_validate(activity)


@router.get(
    "/{activity_id}",
    response_model=ActivityResponse,
    summary="Get an activity by ID",
)
async def get_activity(
    activity_id: UUID,
    current_user: CurrentUser,
    session: DBSession,
) -> ActivityResponse:
    """
    Return a specific activity by ID.

    Args:
        activity_id: UUID of the target activity.
        current_user: Injected authenticated user.
        session: Injected async database session.

    Returns:
        ``ActivityResponse`` for the target activity.

    Raises:
        404 Not Found: If the activity is not found in the tenant.
    """
    svc = ActivityService(session)
    try:
        activity = await svc.get_activity(activity_id, current_user.organization_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return ActivityResponse.model_validate(activity)


@router.put(
    "/{activity_id}",
    response_model=ActivityResponse,
    summary="Update an activity",
)
async def update_activity(
    activity_id: UUID,
    payload: ActivityUpdate,
    current_user: CurrentUser,
    session: DBSession,
) -> ActivityResponse:
    """
    Apply a partial update to an activity.

    Args:
        activity_id: UUID of the activity to update.
        payload: Fields to change.
        current_user: Injected authenticated user.
        session: Injected async database session.

    Returns:
        Updated ``ActivityResponse``.

    Raises:
        403 Forbidden: On permission violation.
        404 Not Found: If the activity is not found.
    """
    svc = ActivityService(session)
    try:
        activity = await svc.update_activity(
            activity_id, payload, current_user.organization_id, current_user
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return ActivityResponse.model_validate(activity)


@router.delete(
    "/{activity_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an activity",
)
async def delete_activity(
    activity_id: UUID,
    current_user: CurrentUser,
    session: DBSession,
) -> None:
    """
    Permanently delete an activity.

    Args:
        activity_id: UUID of the activity to delete.
        current_user: Injected authenticated user.
        session: Injected async database session.

    Raises:
        403 Forbidden: On permission violation.
        404 Not Found: If the activity is not found.
    """
    svc = ActivityService(session)
    try:
        await svc.delete_activity(activity_id, current_user.organization_id, current_user)
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
