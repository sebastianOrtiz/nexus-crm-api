"""
Contacts router — full CRUD plus activities sub-resource.
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from src.api.v1.dependencies import CurrentUser, DBSession
from src.core.enums import ContactSource
from src.core.exceptions import ForbiddenError, NotFoundError
from src.schemas.activity import ActivityResponse
from src.schemas.common import PaginatedResponse
from src.schemas.contact import ContactCreate, ContactResponse, ContactUpdate
from src.services.contact import ContactService

router = APIRouter(prefix="/contacts", tags=["contacts"])


@router.get(
    "",
    response_model=PaginatedResponse[ContactResponse],
    summary="List contacts",
)
async def list_contacts(
    current_user: CurrentUser,
    session: DBSession,
    search: str | None = Query(default=None),
    source: ContactSource | None = Query(default=None),
    company_id: UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[ContactResponse]:
    """
    Return a paginated list of contacts.

    Sales reps see only their assigned contacts. Owners and admins see all.

    Args:
        current_user: Injected authenticated user.
        session: Injected async database session.
        search: Optional substring filter on name or email.
        company_id: Optional filter by company.
        page: Page number (1-indexed).
        page_size: Records per page.

    Returns:
        Paginated ``ContactResponse`` list.
    """
    svc = ContactService(session)
    return await svc.list_contacts(
        current_user.organization_id,
        current_user,
        search=search,
        source=source.value if source else None,
        company_id=company_id,
        page=page,
        page_size=page_size,
    )


@router.post(
    "",
    response_model=ContactResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a contact",
)
async def create_contact(
    payload: ContactCreate,
    current_user: CurrentUser,
    session: DBSession,
) -> ContactResponse:
    """
    Create a new contact in the caller's organization.

    Args:
        payload: Contact creation data.
        current_user: Injected authenticated user.
        session: Injected async database session.

    Returns:
        The newly created ``ContactResponse``.

    Raises:
        403 Forbidden: If the caller is a viewer.
    """
    svc = ContactService(session)
    try:
        contact = await svc.create_contact(payload, current_user.organization_id, current_user)
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    return ContactResponse.model_validate(contact)


@router.get(
    "/{contact_id}",
    response_model=ContactResponse,
    summary="Get a contact by ID",
)
async def get_contact(
    contact_id: UUID,
    current_user: CurrentUser,
    session: DBSession,
) -> ContactResponse:
    """
    Return a specific contact by ID.

    Args:
        contact_id: UUID of the target contact.
        current_user: Injected authenticated user.
        session: Injected async database session.

    Returns:
        ``ContactResponse`` for the target contact.

    Raises:
        404 Not Found: If the contact does not exist in the tenant.
    """
    svc = ContactService(session)
    try:
        contact = await svc.get_contact(contact_id, current_user.organization_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return ContactResponse.model_validate(contact)


@router.put(
    "/{contact_id}",
    response_model=ContactResponse,
    summary="Update a contact",
)
async def update_contact(
    contact_id: UUID,
    payload: ContactUpdate,
    current_user: CurrentUser,
    session: DBSession,
) -> ContactResponse:
    """
    Apply a partial update to a contact.

    Args:
        contact_id: UUID of the contact to update.
        payload: Fields to change.
        current_user: Injected authenticated user.
        session: Injected async database session.

    Returns:
        Updated ``ContactResponse``.

    Raises:
        403 Forbidden: On permission violation.
        404 Not Found: If the contact is not found.
    """
    svc = ContactService(session)
    try:
        contact = await svc.update_contact(
            contact_id, payload, current_user.organization_id, current_user
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return ContactResponse.model_validate(contact)


@router.delete(
    "/{contact_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a contact",
)
async def delete_contact(
    contact_id: UUID,
    current_user: CurrentUser,
    session: DBSession,
) -> None:
    """
    Permanently delete a contact.

    Args:
        contact_id: UUID of the contact to delete.
        current_user: Injected authenticated user.
        session: Injected async database session.

    Raises:
        403 Forbidden: If the caller is not owner or admin.
        404 Not Found: If the contact is not found.
    """
    svc = ContactService(session)
    try:
        await svc.delete_contact(contact_id, current_user.organization_id, current_user)
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get(
    "/{contact_id}/activities",
    response_model=list[ActivityResponse],
    summary="List activities for a contact",
)
async def get_contact_activities(
    contact_id: UUID,
    current_user: CurrentUser,
    session: DBSession,
) -> list[ActivityResponse]:
    """
    Return all activities linked to a specific contact.

    Args:
        contact_id: UUID of the target contact.
        current_user: Injected authenticated user.
        session: Injected async database session.

    Returns:
        List of ``ActivityResponse`` schemas.

    Raises:
        404 Not Found: If the contact is not found.
    """
    svc = ContactService(session)
    try:
        return await svc.get_contact_activities(contact_id, current_user.organization_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
