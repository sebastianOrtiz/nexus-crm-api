"""
Authentication service — handles registration, login and token lifecycle.

Business rules enforced here:
- A new registration creates both the Organization and its first owner User
  in a single transaction.
- Login validates credentials and returns both access and refresh tokens.
- Refresh accepts only a valid refresh token and issues a new access token.
- All operations raise domain exceptions, never HTTP exceptions.
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.constants import JWT_CLAIM_ORG, JWT_CLAIM_SUB
from src.core.enums import OrganizationPlan, UserRole
from src.core.exceptions import ConflictError, UnauthorizedError
from src.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)
from src.core.utils import normalize_email
from src.models.organization import Organization
from src.models.user import User
from src.repositories.organization import OrganizationRepository
from src.repositories.user import UserRepository
from src.schemas.auth import RegisterRequest, TokenResponse


class AuthService:
    """
    Coordinates user authentication and token management.

    Args:
        session: Async database session for the current request scope.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._org_repo = OrganizationRepository(session)
        self._user_repo = UserRepository(session)

    async def register(self, payload: RegisterRequest) -> TokenResponse:
        """
        Create a new organization with the caller as the first ``owner`` user.

        Validates that neither the slug nor the e-mail is already taken before
        writing anything, to keep the error feedback clear.

        Args:
            payload: Validated registration request data.

        Returns:
            ``TokenResponse`` with fresh access and refresh tokens.

        Raises:
            ConflictError: If the slug or e-mail is already registered.
        """
        # Guard: unique slug
        if await self._org_repo.get_by_slug(payload.organization_slug):
            raise ConflictError(f"Organization slug '{payload.organization_slug}' is already taken")

        # Guard: unique email (globally — email is unique across all tenants)
        if await self._user_repo.get_by_email(payload.email):
            raise ConflictError(f"Email '{payload.email}' is already registered")

        # Create organization
        org: Organization = await self._org_repo.create(
            name=payload.organization_name,
            slug=payload.organization_slug,
            plan=OrganizationPlan.FREE.value,
            is_active=True,
        )

        # Create owner user
        user: User = await self._user_repo.create(
            organization_id=org.id,
            email=normalize_email(payload.email),
            password_hash=hash_password(payload.password),
            first_name=payload.first_name,
            last_name=payload.last_name,
            role=UserRole.OWNER.value,
            is_active=True,
            created_at=datetime.now(UTC),
        )

        return TokenResponse(
            access_token=create_access_token(user.id, org.id, user.role),
            refresh_token=create_refresh_token(user.id, org.id),
        )

    async def login(self, email: str, password: str) -> TokenResponse:
        """
        Authenticate a user with e-mail and password.

        Args:
            email: The user's e-mail address.
            password: The plain-text password to verify.

        Returns:
            ``TokenResponse`` with fresh tokens on success.

        Raises:
            UnauthorizedError: If credentials are invalid or the account is
                inactive.
        """
        user = await self._user_repo.get_by_email(normalize_email(email))

        # Use the same generic error for both "not found" and "wrong password"
        # to avoid user enumeration attacks.
        if user is None or not verify_password(password, user.password_hash):
            raise UnauthorizedError("Invalid email or password")

        if not user.is_active:
            raise UnauthorizedError("Account is deactivated")

        return TokenResponse(
            access_token=create_access_token(user.id, user.organization_id, user.role),
            refresh_token=create_refresh_token(user.id, user.organization_id),
        )

    async def refresh(self, refresh_token: str) -> TokenResponse:
        """
        Issue a new access token from a valid refresh token.

        Args:
            refresh_token: The long-lived JWT refresh token.

        Returns:
            New ``TokenResponse`` with a fresh access token. The refresh
            token itself is rotated (a new one is issued).

        Raises:
            UnauthorizedError: If the refresh token is invalid, expired, or
                the user no longer exists.
        """
        payload = decode_refresh_token(refresh_token)
        user_id = UUID(payload[JWT_CLAIM_SUB])
        org_id = UUID(payload[JWT_CLAIM_ORG])

        user = await self._user_repo.get_by_id(user_id)
        if user is None or not user.is_active:
            raise UnauthorizedError("User not found or deactivated")

        return TokenResponse(
            access_token=create_access_token(user.id, org_id, user.role),
            refresh_token=create_refresh_token(user.id, org_id),
        )
