"""
FastAPI dependency functions for authentication and authorisation.

These dependencies follow the Dependency Inversion principle: routers
declare *what* they need (a current user with a minimum role) without
knowing *how* authentication is implemented.

Usage in a router::

    @router.get("/deals")
    async def list_deals(
        current_user: CurrentUser,
        session: DBSession,
    ) -> ...:
        ...
"""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.constants import BEARER_PREFIX, JWT_CLAIM_SUB
from src.core.database import get_session
from src.core.enums import UserRole
from src.core.exceptions import UnauthorizedError
from src.core.security import decode_access_token
from src.models.user import User
from src.repositories.user import UserRepository

# ---------------------------------------------------------------------------
# Re-usable type aliases for Annotated dependencies
# ---------------------------------------------------------------------------

DBSession = Annotated[AsyncSession, Depends(get_session)]

_bearer_scheme = HTTPBearer(auto_error=False)
_BearerCredentials = Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)]


# ---------------------------------------------------------------------------
# Token extraction helper
# ---------------------------------------------------------------------------


def _extract_token(credentials: _BearerCredentials) -> str:
    """
    Extract the raw JWT string from the Authorization header.

    Args:
        credentials: Parsed bearer credentials from FastAPI's security scheme.

    Returns:
        The raw token string.

    Raises:
        HTTPException 401: If the header is missing or does not use the
            ``Bearer`` scheme.
    """
    if credentials is None or credentials.scheme.lower() != BEARER_PREFIX.lower():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials


# ---------------------------------------------------------------------------
# Current-user dependency
# ---------------------------------------------------------------------------


async def get_current_user(
    credentials: _BearerCredentials,
    session: DBSession,
) -> User:
    """
    Validate the bearer token and return the corresponding ``User`` record.

    This is the primary authentication dependency. It decodes the JWT,
    verifies the user exists in the database, and checks the account is
    active.

    Args:
        credentials: HTTP bearer credentials extracted from the request.
        session: Async database session (injected by FastAPI DI).

    Returns:
        The authenticated ``User`` ORM instance.

    Raises:
        HTTPException 401: On any authentication failure.
    """
    token = _extract_token(credentials)
    try:
        payload = decode_access_token(token)
    except UnauthorizedError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user_id: str | None = payload.get(JWT_CLAIM_SUB)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    repo = UserRepository(session)
    user = await repo.get_by_id(UUID(user_id))
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or deactivated",
        )
    return user


# Annotated alias used in route signatures
CurrentUser = Annotated[User, Depends(get_current_user)]


# ---------------------------------------------------------------------------
# Role-based dependency factories
# ---------------------------------------------------------------------------


def require_roles(*roles: UserRole):
    """
    Return a dependency that asserts the current user has one of the given roles.

    Usage::

        @router.delete("/{id}")
        async def delete(
            current_user: Annotated[User, Depends(require_roles(UserRole.OWNER, UserRole.ADMIN))],
        ):
            ...

    Args:
        *roles: One or more ``UserRole`` values that are permitted.

    Returns:
        A FastAPI-compatible async dependency callable.
    """

    async def _check(user: CurrentUser) -> User:
        if UserRole(user.role) not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )
        return user

    return _check


# Convenience aliases for the most common permission gates
OwnerOrAdmin = Annotated[
    User,
    Depends(require_roles(UserRole.OWNER, UserRole.ADMIN)),
]
OwnerOnly = Annotated[
    User,
    Depends(require_roles(UserRole.OWNER)),
]
