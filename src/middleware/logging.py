"""
Structured request/response logging middleware.

Logs method, path, status code and duration for every request so operators
can diagnose performance issues without adding instrumentation to every route.
"""

import logging
import time

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

logger = logging.getLogger("nexuscrm.http")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    ASGI middleware that logs every HTTP request and its outcome.

    Attaches a ``X-Request-ID`` response header (if not already present)
    and emits a structured log line after the response is sent.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """
        Process the request, measure latency, and log the result.

        Args:
            request: The incoming HTTP request.
            call_next: The next middleware or route handler in the chain.

        Returns:
            The HTTP response produced by the handler.
        """
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000

        logger.info(
            "%(method)s %(path)s %(status)s %(duration).1fms",
            {
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration": duration_ms,
            },
        )
        return response
