"""
Domain enumerations shared across models, schemas, and services.

Using Python's ``enum.Enum`` (not plain strings) guarantees that the compiler
catches typos and that OpenAPI documents the allowed values automatically.
"""

from enum import Enum


class UserRole(str, Enum):
    """Roles a user can hold within an organization."""

    OWNER = "owner"
    ADMIN = "admin"
    SALES_REP = "sales_rep"
    VIEWER = "viewer"


class OrganizationPlan(str, Enum):
    """Subscription plans available for an organization."""

    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class ActivityType(str, Enum):
    """Type of a CRM activity."""

    CALL = "call"
    EMAIL = "email"
    MEETING = "meeting"
    NOTE = "note"


class ContactSource(str, Enum):
    """Channel through which a contact was acquired."""

    WEBSITE = "website"
    REFERRAL = "referral"
    COLD_OUTREACH = "cold_outreach"
    SOCIAL_MEDIA = "social_media"
    EVENT = "event"
    OTHER = "other"


class DealCurrency(str, Enum):
    """ISO 4217 currency codes supported for deal values."""

    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    MXN = "MXN"
    COP = "COP"
    ARS = "ARS"


class TokenType(str, Enum):
    """Distinguishes access tokens from refresh tokens in the payload."""

    ACCESS = "access"
    REFRESH = "refresh"
