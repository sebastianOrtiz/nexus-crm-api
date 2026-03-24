"""
Shared helper utilities for API v1 routers.

These helpers centralise cross-cutting concerns (pagination clamping, etc.)
so that routers stay thin and free of duplicated logic.
"""

from src.core.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE


def clamp_page_size(page_size: int) -> int:
    """
    Clamp page_size to valid range [1, MAX_PAGE_SIZE].

    Values below 1 are replaced with DEFAULT_PAGE_SIZE.
    Values above MAX_PAGE_SIZE are capped at MAX_PAGE_SIZE.

    Args:
        page_size: The requested page size from the query parameter.

    Returns:
        A safe page size within the accepted bounds.
    """
    if page_size < 1:
        return DEFAULT_PAGE_SIZE
    return min(page_size, MAX_PAGE_SIZE)
