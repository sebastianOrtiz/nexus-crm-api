"""
Onboarding integration service — triggers the event-driven onboarding flow.

Calls the event-driven-service API to start the asynchronous onboarding
pipeline when a new user registers. Failures are logged but never block
the registration flow (fire-and-forget).
"""

import logging

import httpx

from src.core.config import settings

logger = logging.getLogger("nexuscrm.onboarding")

TRIGGER_PATH = "/api/v1/onboarding/trigger"
TIMEOUT_SECONDS = 5


async def trigger_onboarding(
    email: str,
    name: str,
    org_name: str,
) -> str | None:
    """
    Fire-and-forget call to the event-driven onboarding service.

    Args:
        email: The new user's email address.
        name: The new user's full name.
        org_name: The organization name.

    Returns:
        The correlation ID string if successful, None on failure.
    """
    url = f"{settings.EVENT_SERVICE_URL}{TRIGGER_PATH}"
    payload = {
        "email": email,
        "name": name,
        "orgName": org_name,
    }

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
            response = await client.post(url, json=payload)

        if response.status_code in (200, 201, 202):
            data = response.json()
            correlation_id = data.get("correlationId")
            logger.info(
                "Onboarding triggered",
                extra={
                    "correlation_id": correlation_id,
                    "email": email,
                },
            )
            return correlation_id

        logger.warning(
            "Onboarding trigger returned non-success status",
            extra={
                "status_code": response.status_code,
                "body": response.text[:200],
                "email": email,
            },
        )
    except httpx.ConnectError:
        logger.warning(
            "Event service unavailable — onboarding skipped",
            extra={"url": url, "email": email},
        )
    except Exception:
        logger.exception(
            "Unexpected error triggering onboarding",
            extra={"email": email},
        )

    return None
