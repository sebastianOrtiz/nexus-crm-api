"""
Authentication router — register, login, refresh, logout.
"""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import DBSession
from src.core.exceptions import ConflictError, UnauthorizedError
from src.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from src.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def _get_auth_service(session: AsyncSession) -> AuthService:
    """Construct the auth service for the current request session."""
    return AuthService(session)


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new organization and owner user",
)
async def register(payload: RegisterRequest, session: DBSession) -> TokenResponse:
    """
    Create a new organization with the caller as the first ``owner`` user.

    Returns access and refresh tokens so the client is immediately
    authenticated after registration.

    Args:
        payload: Organization name/slug and owner user credentials.
        session: Injected async database session.

    Returns:
        ``TokenResponse`` with fresh JWT tokens.

    Raises:
        409 Conflict: If the organization slug or e-mail is already taken.
    """
    try:
        return await _get_auth_service(session).register(payload)
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and receive JWT tokens",
)
async def login(payload: LoginRequest, session: DBSession) -> TokenResponse:
    """
    Authenticate with e-mail and password.

    Args:
        payload: E-mail and password credentials.
        session: Injected async database session.

    Returns:
        ``TokenResponse`` with access and refresh tokens.

    Raises:
        401 Unauthorized: On invalid credentials or deactivated account.
    """
    try:
        return await _get_auth_service(session).login(payload.email, payload.password)
    except UnauthorizedError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
)
async def refresh(payload: RefreshRequest, session: DBSession) -> TokenResponse:
    """
    Exchange a valid refresh token for a new access token.

    Args:
        payload: The refresh token.
        session: Injected async database session.

    Returns:
        New ``TokenResponse`` with rotated tokens.

    Raises:
        401 Unauthorized: If the refresh token is invalid or expired.
    """
    try:
        return await _get_auth_service(session).refresh(payload.refresh_token)
    except UnauthorizedError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout (client-side token invalidation)",
)
async def logout(payload: LogoutRequest) -> None:
    """
    Logout endpoint.

    This implementation is stateless — JWTs cannot be revoked server-side
    without a token blacklist. The client must discard both tokens locally.

    A token blacklist with Redis would be the production-grade enhancement;
    this endpoint exists to give the client a semantically correct call to
    make and to document the expected client behaviour.

    Args:
        payload: The refresh token being invalidated (client must discard it).
    """
    # Stateless logout: client discards tokens.
    # Future enhancement: add refresh_token to a Redis blacklist.
    return None
