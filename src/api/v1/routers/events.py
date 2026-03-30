"""
Events proxy router — proxies requests to the event-driven service.

Provides CRM dashboard users with read-only access to onboarding flows
and events from the event-driven-service without exposing the internal
service URL to the frontend.
"""

import logging
from typing import Any

import httpx
from fastapi import APIRouter

from src.api.v1.dependencies import CurrentUser
from src.core.config import settings

logger = logging.getLogger("nexuscrm.events")

router = APIRouter(prefix="/events", tags=["events"])

TIMEOUT_SECONDS = 5


async def _proxy_get(path: str) -> list[dict[str, Any]]:
    """
    Forward a GET request to the event service and return parsed JSON.

    Args:
        path: The path to append to EVENT_SERVICE_URL.

    Returns:
        The parsed JSON response as a list, or an empty list on failure.
    """
    url = f"{settings.EVENT_SERVICE_URL}{path}"
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
            response = await client.get(url)

        if response.status_code == 200:
            return response.json()  # type: ignore[no-any-return]

        logger.warning(
            "Event service returned non-200",
            extra={"status_code": response.status_code, "path": path},
        )
    except httpx.ConnectError:
        logger.warning(
            "Event service unavailable",
            extra={"url": url},
        )
    except Exception:
        logger.exception("Unexpected error proxying to event service")

    return []


@router.get(
    "/flows",
    summary="List onboarding flows",
    response_model=list[dict[str, Any]],
)
async def get_flows(current_user: CurrentUser) -> list[dict[str, Any]]:
    """
    Proxy to the event service to retrieve all onboarding flows.

    Args:
        current_user: Injected authenticated user (any role).

    Returns:
        List of onboarding flow objects.
    """
    return await _proxy_get("/api/v1/onboarding")


@router.get(
    "/all",
    summary="List all onboarding events",
    response_model=list[dict[str, Any]],
)
async def get_all_events(current_user: CurrentUser) -> list[dict[str, Any]]:
    """
    Proxy to the event service to retrieve all onboarding events.

    Args:
        current_user: Injected authenticated user (any role).

    Returns:
        List of onboarding event objects.
    """
    return await _proxy_get("/api/v1/onboarding/events")
