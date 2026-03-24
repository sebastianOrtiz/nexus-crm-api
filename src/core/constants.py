"""
Application-wide constants.

No magic strings or numbers anywhere else in the codebase — all shared
literals live here so a single change propagates everywhere.
"""

# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------

ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
"""Lifetime of an access token in minutes."""

REFRESH_TOKEN_EXPIRE_DAYS: int = 7
"""Lifetime of a refresh token in days."""

JWT_ALGORITHM: str = "HS256"
"""Algorithm used to sign JWTs."""

# JWT payload keys
JWT_CLAIM_SUB = "sub"
JWT_CLAIM_ORG = "org"
JWT_CLAIM_ROLE = "role"
JWT_CLAIM_TYPE = "type"
JWT_CLAIM_EXP = "exp"
JWT_CLAIM_IAT = "iat"

# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------

DEFAULT_PAGE_SIZE: int = 20
"""Number of items returned per page when no limit is specified."""

MAX_PAGE_SIZE: int = 100
"""Hard upper-bound for page size to prevent accidental full-table reads."""

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

DB_SCHEMA: str = "crm"
"""PostgreSQL schema used by all CRM tables."""

# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

BCRYPT_ROUNDS: int = 12
"""Work factor for bcrypt. Higher = slower and more secure."""

# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

BEARER_PREFIX: str = "Bearer"
"""Expected prefix in the Authorization header."""
