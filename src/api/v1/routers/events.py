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

API_KEY_HEADER = "X-API-Key"
TIMEOUT_SECONDS = 5


async def _proxy_get(path: str) -> dict[str, Any]:
    """
    Forward a GET request to the event service and return parsed JSON.

    Returns:
        The parsed JSON response, or a dict with empty lists on failure.
    """
    url = f"{settings.EVENT_SERVICE_URL}{path}"
    headers = {API_KEY_HEADER: settings.EVENT_SERVICE_API_KEY}
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
            response = await client.get(url, headers=headers)

        if response.status_code == 200:
            return response.json()  # type: ignore[no-any-return]

        logger.warning(
            "Event service returned non-200",
            extra={"status_code": response.status_code, "path": path},
        )
    except httpx.ConnectError:
        logger.warning("Event service unavailable", extra={"url": url})
    except Exception:
        logger.exception("Unexpected error proxying to event service")

    return {}


@router.get("/flows", summary="List onboarding flows")
async def get_flows(current_user: CurrentUser) -> dict[str, Any]:
    """Proxy to the event service to retrieve all onboarding flows."""
    return await _proxy_get("/api/v1/onboarding")


@router.get("/all", summary="List all onboarding events")
async def get_all_events(current_user: CurrentUser) -> dict[str, Any]:
    """Proxy to the event service to retrieve all onboarding events."""
    return await _proxy_get("/api/v1/onboarding/events")
