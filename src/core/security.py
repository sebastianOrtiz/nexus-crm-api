"""
Security utilities: password hashing and JWT management.

Responsibilities of this module (Single Responsibility: auth primitives only):
- Hash and verify passwords with bcrypt.
- Create and decode JWT access/refresh tokens.
- Raise ``UnauthorizedError`` on any token failure so callers don't need to
  know the details of the JWT library.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from jose import ExpiredSignatureError, JWTError, jwt
from passlib.context import CryptContext

from src.core.config import settings
from src.core.constants import (
    JWT_ALGORITHM,
    JWT_CLAIM_EMAIL,
    JWT_CLAIM_EXP,
    JWT_CLAIM_IAT,
    JWT_CLAIM_NAME,
    JWT_CLAIM_ORG,
    JWT_CLAIM_ROLE,
    JWT_CLAIM_SUB,
    JWT_CLAIM_TYPE,
)
from src.core.enums import TokenType
from src.core.exceptions import UnauthorizedError

# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    """
    Hash a plain-text password using bcrypt.

    Args:
        plain: The raw password provided by the user.

    Returns:
        A bcrypt hash string safe to store in the database.
    """
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """
    Verify a plain-text password against its bcrypt hash.

    Args:
        plain: The raw password to check.
        hashed: The stored bcrypt hash.

    Returns:
        ``True`` if the password matches, ``False`` otherwise.
    """
    return _pwd_context.verify(plain, hashed)


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------


def _now_utc() -> datetime:
    """Return the current UTC time as a timezone-aware datetime."""
    return datetime.now(UTC)


def create_access_token(
    user_id: UUID,
    organization_id: UUID,
    role: str,
    email: str,
    name: str = "",
) -> str:
    """
    Create a short-lived JWT access token.

    The payload contains ``sub`` (user ID), ``org`` (organization ID),
    ``role``, ``email``, ``name``, ``type``, and ``exp``.

    Args:
        user_id: UUID of the authenticated user.
        organization_id: UUID of the user's organization (tenant).
        role: The user's role string (e.g., ``"owner"``).
        email: The user's email address.
        name: The user's display name.

    Returns:
        Signed JWT string.
    """
    expire = _now_utc() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        JWT_CLAIM_SUB: str(user_id),
        JWT_CLAIM_ORG: str(organization_id),
        JWT_CLAIM_ROLE: role,
        JWT_CLAIM_EMAIL: email,
        JWT_CLAIM_NAME: name,
        JWT_CLAIM_TYPE: TokenType.ACCESS.value,
        JWT_CLAIM_EXP: expire,
        JWT_CLAIM_IAT: _now_utc(),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: UUID, organization_id: UUID) -> str:
    """
    Create a long-lived JWT refresh token.

    Refresh tokens carry only ``sub``, ``org``, and ``type`` — they must
    not be used to authorize resource access directly.

    Args:
        user_id: UUID of the authenticated user.
        organization_id: UUID of the user's organization.

    Returns:
        Signed JWT string.
    """
    expire = _now_utc() + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        JWT_CLAIM_SUB: str(user_id),
        JWT_CLAIM_ORG: str(organization_id),
        JWT_CLAIM_TYPE: TokenType.REFRESH.value,
        JWT_CLAIM_EXP: expire,
        JWT_CLAIM_IAT: _now_utc(),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """
    Decode and validate a JWT token.

    Args:
        token: The raw JWT string from the Authorization header.

    Returns:
        The decoded payload dictionary.

    Raises:
        UnauthorizedError: If the token is expired, malformed, or has an
            invalid signature.
    """
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except ExpiredSignatureError as exc:
        raise UnauthorizedError("Token has expired") from exc
    except JWTError as exc:
        raise UnauthorizedError("Could not validate credentials") from exc


def decode_access_token(token: str) -> dict:
    """
    Decode a token and assert it is an access token.

    Args:
        token: Raw JWT string.

    Returns:
        Decoded payload.

    Raises:
        UnauthorizedError: If the token is invalid or is not an access token.
    """
    payload = decode_token(token)
    if payload.get(JWT_CLAIM_TYPE) != TokenType.ACCESS.value:
        raise UnauthorizedError("Invalid token type")
    return payload


def decode_refresh_token(token: str) -> dict:
    """
    Decode a token and assert it is a refresh token.

    Args:
        token: Raw JWT string.

    Returns:
        Decoded payload.

    Raises:
        UnauthorizedError: If the token is invalid or is not a refresh token.
    """
    payload = decode_token(token)
    if payload.get(JWT_CLAIM_TYPE) != TokenType.REFRESH.value:
        raise UnauthorizedError("Invalid token type")
    return payload
