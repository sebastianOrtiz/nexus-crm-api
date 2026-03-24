"""
Companies router — full CRUD plus contacts sub-resource.
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from src.api.v1.dependencies import CurrentUser, DBSession
from src.core.exceptions import ForbiddenError, NotFoundError
from src.schemas.common import PaginatedResponse
from src.schemas.company import CompanyCreate, CompanyResponse, CompanyUpdate
from src.schemas.contact import ContactResponse
from src.services.company import CompanyService

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get(
    "",
    response_model=PaginatedResponse[CompanyResponse],
    summary="List companies",
)
async def list_companies(
    current_user: CurrentUser,
    session: DBSession,
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[CompanyResponse]:
    """
    Return a paginated, searchable list of companies.

    Args:
        current_user: Injected authenticated user.
        session: Injected async database session.
        search: Optional substring filter on name or domain.
        page: Page number (1-indexed).
        page_size: Records per page.

    Returns:
        Paginated ``CompanyResponse`` list.
    """
    svc = CompanyService(session)
    return await svc.list_companies(
        current_user.organization_id, search=search, page=page, page_size=page_size
    )


@router.post(
    "",
    response_model=CompanyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a company",
)
async def create_company(
    payload: CompanyCreate,
    current_user: CurrentUser,
    session: DBSession,
) -> CompanyResponse:
    """
    Create a new company.

    Args:
        payload: Company creation data.
        current_user: Injected authenticated user.
        session: Injected async database session.

    Returns:
        The newly created ``CompanyResponse``.

    Raises:
        403 Forbidden: If the caller is a viewer.
    """
    svc = CompanyService(session)
    try:
        company = await svc.create_company(payload, current_user.organization_id, current_user)
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    return CompanyResponse.model_validate(company)


@router.get(
    "/{company_id}",
    response_model=CompanyResponse,
    summary="Get a company by ID",
)
async def get_company(
    company_id: UUID, current_user: CurrentUser, session: DBSession
) -> CompanyResponse:
    """
    Return a specific company by ID.

    Args:
        company_id: UUID of the target company.
        current_user: Injected authenticated user.
        session: Injected async database session.

    Returns:
        ``CompanyResponse`` for the target company.

    Raises:
        404 Not Found: If the company is not found in the tenant.
    """
    svc = CompanyService(session)
    try:
        company = await svc.get_company(company_id, current_user.organization_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return CompanyResponse.model_validate(company)


@router.put(
    "/{company_id}",
    response_model=CompanyResponse,
    summary="Update a company",
)
async def update_company(
    company_id: UUID,
    payload: CompanyUpdate,
    current_user: CurrentUser,
    session: DBSession,
) -> CompanyResponse:
    """
    Apply a partial update to a company.

    Args:
        company_id: UUID of the company to update.
        payload: Fields to change.
        current_user: Injected authenticated user.
        session: Injected async database session.

    Returns:
        Updated ``CompanyResponse``.

    Raises:
        403 Forbidden: On permission violation.
        404 Not Found: If the company is not found.
    """
    svc = CompanyService(session)
    try:
        company = await svc.update_company(
            company_id, payload, current_user.organization_id, current_user
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return CompanyResponse.model_validate(company)


@router.delete(
    "/{company_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a company",
)
async def delete_company(
    company_id: UUID,
    current_user: CurrentUser,
    session: DBSession,
) -> None:
    """
    Permanently delete a company.

    Args:
        company_id: UUID of the company to delete.
        current_user: Injected authenticated user.
        session: Injected async database session.

    Raises:
        403 Forbidden: If the caller is not owner or admin.
        404 Not Found: If the company is not found.
    """
    svc = CompanyService(session)
    try:
        await svc.delete_company(company_id, current_user.organization_id, current_user)
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get(
    "/{company_id}/contacts",
    response_model=list[ContactResponse],
    summary="List contacts for a company",
)
async def get_company_contacts(
    company_id: UUID,
    current_user: CurrentUser,
    session: DBSession,
) -> list[ContactResponse]:
    """
    Return all contacts associated with a company.

    Args:
        company_id: UUID of the target company.
        current_user: Injected authenticated user.
        session: Injected async database session.

    Returns:
        List of ``ContactResponse`` schemas.

    Raises:
        404 Not Found: If the company is not found.
    """
    svc = CompanyService(session)
    try:
        return await svc.get_company_contacts(company_id, current_user.organization_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
