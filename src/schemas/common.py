"""
Shared Pydantic building blocks used across all feature schemas.
"""

from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class CamelModel(BaseModel):
    """
    Base model that serialises field names as camelCase.

    The Angular frontend expects camelCase JSON, so all response schemas
    inherit from this base.
    """

    model_config = ConfigDict(
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

    model_config = ConfigDict(from_attributes=True)


class IDResponse(BaseModel):
    """Minimal response that returns only the ID of a created/modified resource."""

    id: UUID
