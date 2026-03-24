"""
Company service — CRUD and permission checks for Company records.
"""

import math
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from src.core.enums import UserRole
from src.core.exceptions import ForbiddenError, NotFoundError
from src.models.company import Company
from src.models.user import User
from src.repositories.company import CompanyRepository
from src.repositories.contact import ContactRepository
from src.schemas.common import PaginatedResponse
from src.schemas.company import CompanyCreate, CompanyResponse, CompanyUpdate
from src.schemas.contact import ContactResponse


class CompanyService:
    """
    Business logic for company management.

    Args:
        session: Async database session.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._repo = CompanyRepository(session)
        self._contact_repo = ContactRepository(session)

    def _can_write(self, user: User) -> bool:
        """Return True if the user may create or modify companies."""
        return UserRole(user.role) in (UserRole.OWNER, UserRole.ADMIN, UserRole.SALES_REP)

    async def list_companies(
        self,
        organization_id: UUID,
        *,
        search: str | None = None,
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> PaginatedResponse[CompanyResponse]:
        """
        Return a paginated list of companies.

        Args:
            organization_id: Tenant boundary UUID.
            search: Optional substring filter on name or domain.
            page: 1-indexed page number.
            page_size: Records per page.

        Returns:
            Paginated response envelope.
        """
        page_size = min(page_size, MAX_PAGE_SIZE)
        offset = (page - 1) * page_size
        companies, total = await self._repo.list_by_org(
            organization_id, search=search, offset=offset, limit=page_size
        )
        pages = math.ceil(total / page_size) if total else 1
        return PaginatedResponse(
            items=[CompanyResponse.model_validate(c) for c in companies],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )

    async def get_company(self, company_id: UUID, organization_id: UUID) -> Company:
        """
        Fetch a company by ID within a tenant.

        Args:
            company_id: UUID of the target company.
            organization_id: Tenant boundary UUID.

        Returns:
            The ``Company`` ORM instance.

        Raises:
            NotFoundError: If not found in the tenant.
        """
        company = await self._repo.get_by_id_and_org(company_id, organization_id)
        if company is None:
            raise NotFoundError("Company", str(company_id))
        return company

    async def create_company(
        self,
        payload: CompanyCreate,
        organization_id: UUID,
        current_user: User,
    ) -> Company:
        """
        Create a new company.

        Args:
            payload: Validated creation data.
            organization_id: Tenant boundary UUID.
            current_user: The requesting user.

        Returns:
            The new ``Company`` instance.

        Raises:
            ForbiddenError: If the user does not have write access.
        """
        if not self._can_write(current_user):
            raise ForbiddenError("Viewers cannot create companies")

        return await self._repo.create(
            organization_id=organization_id,
            **payload.model_dump(),
        )

    async def update_company(
        self,
        company_id: UUID,
        payload: CompanyUpdate,
        organization_id: UUID,
        current_user: User,
    ) -> Company:
        """
        Apply a partial update to a company.

        Args:
            company_id: UUID of the company to update.
            payload: Fields to change.
            organization_id: Tenant boundary UUID.
            current_user: The requesting user.

        Returns:
            The updated ``Company`` instance.

        Raises:
            ForbiddenError: On permission violation.
            NotFoundError: If the company is not found.
        """
        if not self._can_write(current_user):
            raise ForbiddenError("Viewers cannot update companies")

        company = await self._repo.get_by_id_and_org(company_id, organization_id)
        if company is None:
            raise NotFoundError("Company", str(company_id))

        changes = payload.model_dump(exclude_none=True)
        if not changes:
            return company

        return await self._repo.update(company, **changes)

    async def delete_company(
        self,
        company_id: UUID,
        organization_id: UUID,
        current_user: User,
    ) -> None:
        """
        Delete a company permanently.

        Args:
            company_id: UUID of the company to delete.
            organization_id: Tenant boundary UUID.
            current_user: The requesting user.

        Raises:
            ForbiddenError: If the user is not owner or admin.
            NotFoundError: If the company is not found.
        """
        if UserRole(current_user.role) not in (UserRole.OWNER, UserRole.ADMIN):
            raise ForbiddenError("Only owners and admins can delete companies")

        company = await self._repo.get_by_id_and_org(company_id, organization_id)
        if company is None:
            raise NotFoundError("Company", str(company_id))

        await self._repo.delete(company)

    async def get_company_contacts(
        self, company_id: UUID, organization_id: UUID
    ) -> list[ContactResponse]:
        """
        Return all contacts linked to a company within the tenant.

        Args:
            company_id: UUID of the target company.
            organization_id: Tenant boundary UUID.

        Returns:
            List of ``ContactResponse`` schemas.

        Raises:
            NotFoundError: If the company is not found.
        """
        company = await self._repo.get_by_id_and_org(company_id, organization_id)
        if company is None:
            raise NotFoundError("Company", str(company_id))

        contacts = await self._contact_repo.list_by_company(company_id, organization_id)
        return [ContactResponse.model_validate(c) for c in contacts]
