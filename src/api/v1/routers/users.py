"""
Users router — CRUD for users within an organization.
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from src.api.v1.dependencies import CurrentUser, DBSession
from src.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from src.schemas.common import PaginatedResponse
from src.schemas.user import UserCreate, UserMeUpdate, UserResponse, UserUpdate
from src.services.user import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse, summary="Get my profile")
async def get_me(current_user: CurrentUser) -> UserResponse:
    """
    Return the profile of the currently authenticated user.

    Args:
        current_user: Injected authenticated user.

    Returns:
        ``UserResponse`` for the caller.
    """
    return UserResponse.model_validate(current_user)


@router.put("/me", response_model=UserResponse, summary="Update my profile")
async def update_me(
    payload: UserMeUpdate,
    current_user: CurrentUser,
    session: DBSession,
) -> UserResponse:
    """
    Allow a user to update their own first/last name.

    Args:
        payload: Fields to update.
        current_user: Injected authenticated user.
        session: Injected async database session.

    Returns:
        Updated ``UserResponse``.
    """
    svc = UserService(session)
    update_payload = UserUpdate(
        first_name=payload.first_name,
        last_name=payload.last_name,
    )
    user = await svc.update_user(current_user.id, update_payload, current_user.organization_id, current_user)
    return UserResponse.model_validate(user)


@router.get("", response_model=PaginatedResponse[UserResponse], summary="List users")
async def list_users(
    current_user: CurrentUser,
    session: DBSession,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[UserResponse]:
    """
    Return a paginated list of users in the caller's organization.

    Args:
        current_user: Injected authenticated user.
        session: Injected async database session.
        page: Page number (1-indexed).
        page_size: Records per page.

    Returns:
        Paginated ``UserResponse`` list.
    """
    svc = UserService(session)
    return await svc.list_users(current_user.organization_id, page=page, page_size=page_size)


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Invite/create a user",
)
async def create_user(
    payload: UserCreate,
    current_user: CurrentUser,
    session: DBSession,
) -> UserResponse:
    """
    Create a new user in the organization. Requires owner or admin role.

    Args:
        payload: User creation data.
        current_user: Injected authenticated user.
        session: Injected async database session.

    Returns:
        The newly created ``UserResponse``.

    Raises:
        403 Forbidden: If the caller is not owner or admin.
        409 Conflict: If the e-mail is already registered.
    """
    svc = UserService(session)
    try:
        user = await svc.create_user(payload, current_user.organization_id, current_user)
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return UserResponse.model_validate(user)


@router.get("/{user_id}", response_model=UserResponse, summary="Get a user by ID")
async def get_user(user_id: UUID, current_user: CurrentUser, session: DBSession) -> UserResponse:
    """
    Return a specific user by ID within the caller's organization.

    Args:
        user_id: UUID of the target user.
        current_user: Injected authenticated user.
        session: Injected async database session.

    Returns:
        ``UserResponse`` for the target user.

    Raises:
        404 Not Found: If the user does not exist in the tenant.
    """
    svc = UserService(session)
    try:
        user = await svc.get_user(user_id, current_user.organization_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return UserResponse.model_validate(user)


@router.put("/{user_id}", response_model=UserResponse, summary="Update a user")
async def update_user(
    user_id: UUID,
    payload: UserUpdate,
    current_user: CurrentUser,
    session: DBSession,
) -> UserResponse:
    """
    Update a user's role or profile. Requires owner or admin.

    Args:
        user_id: UUID of the user to update.
        payload: Fields to change.
        current_user: Injected authenticated user.
        session: Injected async database session.

    Returns:
        Updated ``UserResponse``.

    Raises:
        403 Forbidden: On permission violation.
        404 Not Found: If the user is not found.
    """
    svc = UserService(session)
    try:
        user = await svc.update_user(user_id, payload, current_user.organization_id, current_user)
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return UserResponse.model_validate(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Deactivate a user")
async def delete_user(
    user_id: UUID,
    current_user: CurrentUser,
    session: DBSession,
) -> None:
    """
    Soft-deactivate a user (sets ``is_active=False``).

    Args:
        user_id: UUID of the user to deactivate.
        current_user: Injected authenticated user.
        session: Injected async database session.

    Raises:
        403 Forbidden: On permission violation.
        404 Not Found: If the user is not found.
    """
    svc = UserService(session)
    try:
        await svc.delete_user(user_id, current_user.organization_id, current_user)
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
