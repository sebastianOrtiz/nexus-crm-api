"""
Organization router — get and update the caller's organization.
"""

from fastapi import APIRouter, HTTPException, status

from src.api.v1.dependencies import CurrentUser, DBSession
from src.core.exceptions import ForbiddenError, NotFoundError
from src.schemas.organization import OrganizationResponse, OrganizationUpdate
from src.services.organization import OrganizationService

router = APIRouter(prefix="/organization", tags=["organization"])


@router.get(
    "",
    response_model=OrganizationResponse,
    summary="Get the current organization",
)
async def get_organization(current_user: CurrentUser, session: DBSession) -> OrganizationResponse:
    """
    Return the organization that the authenticated user belongs to.

    Args:
        current_user: Injected authenticated user.
        session: Injected async database session.

    Returns:
        ``OrganizationResponse`` for the caller's tenant.
    """
    svc = OrganizationService(session)
    org = await svc.get(current_user.organization_id)
    return OrganizationResponse.model_validate(org)


@router.put(
    "",
    response_model=OrganizationResponse,
    summary="Update the current organization (owner only)",
)
async def update_organization(
    payload: OrganizationUpdate,
    current_user: CurrentUser,
    session: DBSession,
) -> OrganizationResponse:
    """
    Update mutable fields on the organization.

    Only the ``owner`` role may perform this operation.

    Args:
        payload: Fields to update (all optional).
        current_user: Injected authenticated user.
        session: Injected async database session.

    Returns:
        Updated ``OrganizationResponse``.

    Raises:
        403 Forbidden: If the caller is not the organization owner.
        404 Not Found: If the organization does not exist.
    """
    svc = OrganizationService(session)
    try:
        org = await svc.update(current_user.organization_id, payload, current_user)
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return OrganizationResponse.model_validate(org)
