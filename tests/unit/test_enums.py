"""
Unit tests for domain enumerations.

Ensures that enum values are the expected strings so serialisation to/from
the database and JSON never silently breaks.
"""

from src.core.enums import (
    ActivityType,
    OrganizationPlan,
    TokenType,
    UserRole,
)


class TestUserRole:
    def test_values(self) -> None:
        assert UserRole.OWNER.value == "owner"
        assert UserRole.ADMIN.value == "admin"
        assert UserRole.SALES_REP.value == "sales_rep"
        assert UserRole.VIEWER.value == "viewer"

    def test_from_string(self) -> None:
        assert UserRole("owner") is UserRole.OWNER


class TestActivityType:
    def test_values(self) -> None:
        assert ActivityType.CALL.value == "call"
        assert ActivityType.EMAIL.value == "email"
        assert ActivityType.MEETING.value == "meeting"
        assert ActivityType.NOTE.value == "note"


class TestOrganizationPlan:
    def test_values(self) -> None:
        assert OrganizationPlan.FREE.value == "free"
        assert OrganizationPlan.PROFESSIONAL.value == "professional"


class TestTokenType:
    def test_values(self) -> None:
        assert TokenType.ACCESS.value == "access"
        assert TokenType.REFRESH.value == "refresh"
