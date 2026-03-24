"""
Shared Pydantic building blocks used across all feature schemas.
"""

from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

T = TypeVar("T")


class CamelModel(BaseModel):
    """
    Base model that serialises field names as camelCase.

    The Angular frontend expects camelCase JSON, so all response schemas
    inherit from this base.  ``alias_generator=to_camel`` converts
    ``snake_case`` Python attributes to ``camelCase`` when serialising to
    JSON and when parsing incoming JSON bodies.  ``populate_by_name=True``
    keeps both the original snake_case name and the camelCase alias valid
    for construction (useful in tests and internal code).
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Generic paginated envelope returned by list endpoints.

    Attributes:
        items: The slice of records for the requested page.
        total: Total number of records matching the query (across all pages).
        page: Current page number (1-indexed).
        page_size: Maximum items per page requested.
        pages: Total number of pages.
    """

    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class IDResponse(BaseModel):
    """Minimal response that returns only the ID of a created/modified resource."""

    id: UUID
