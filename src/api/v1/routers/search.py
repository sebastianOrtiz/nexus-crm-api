"""
Search proxy router — proxies requests to the semantic-search-api service.

Provides CRM dashboard users with document management and semantic search
capabilities without exposing the internal search service URL to the frontend.

All endpoints require a valid JWT session (``CurrentUser`` dependency).
The proxy uses a 30-second timeout to accommodate potentially slow file upload
and embedding operations.
"""

import logging
from typing import Any
from uuid import UUID

import httpx
from fastapi import APIRouter, HTTPException, UploadFile, status

from src.api.v1.dependencies import CurrentUser
from src.core.config import settings

logger = logging.getLogger("nexuscrm.search")

router = APIRouter(prefix="/search", tags=["search"])

TIMEOUT_SECONDS = 30


def _build_url(path: str) -> str:
    """Return the full URL for a path on the search service."""
    return f"{settings.SEARCH_SERVICE_URL}{path}"


async def _proxy_get(path: str) -> dict[str, Any]:
    """
    Forward a GET request to the search service and return parsed JSON.

    Args:
        path: The path to forward (e.g. ``/api/v1/documents``).

    Returns:
        The parsed JSON response, or an empty dict on failure.
    """
    url = _build_url(path)
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
            response = await client.get(url)

        if response.status_code == 200:
            return response.json()  # type: ignore[no-any-return]

        logger.warning(
            "Search service returned non-200 on GET",
            extra={"status_code": response.status_code, "path": path},
        )
    except httpx.ConnectError:
        logger.warning("Search service unavailable", extra={"url": url})
    except Exception:
        logger.exception("Unexpected error proxying GET to search service")

    return {}


async def _proxy_delete(path: str) -> dict[str, Any]:
    """
    Forward a DELETE request to the search service and return parsed JSON.

    Args:
        path: The path to forward (e.g. ``/api/v1/documents/{id}``).

    Returns:
        The parsed JSON response on success.

    Raises:
        HTTPException: 404 if the document was not found on the search service,
            503 if the search service is unreachable.
    """
    url = _build_url(path)
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
            response = await client.delete(url)

        if response.status_code == 200:
            return response.json()  # type: ignore[no-any-return]

        if response.status_code == 404:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

        logger.warning(
            "Search service returned non-200 on DELETE",
            extra={"status_code": response.status_code, "path": path},
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unexpected response from search service",
        )
    except HTTPException:
        raise
    except httpx.ConnectError as err:
        logger.warning("Search service unavailable", extra={"url": url})
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Search service is currently unavailable",
        ) from err
    except Exception as err:
        logger.exception("Unexpected error proxying DELETE to search service")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Error communicating with search service",
        ) from err


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/documents/upload", summary="Upload a document for indexing")
async def upload_document(
    current_user: CurrentUser,
    file: UploadFile,
) -> dict[str, Any]:
    """
    Proxy a multipart file upload to the semantic search service for indexing.

    The file is streamed to the search service as-is. Embedding and storage
    happen entirely within the search service.

    Args:
        current_user: Authenticated CRM user (injected by FastAPI DI).
        file: The document to index (PDF, TXT, etc.).

    Returns:
        The parsed JSON response from the search service (document metadata).

    Raises:
        HTTPException: 503 if the search service is unreachable,
            502 on any other upstream error.
    """
    url = _build_url("/api/v1/documents/upload")
    files = {"file": (file.filename, await file.read(), file.content_type)}
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
            response = await client.post(url, files=files)

        if response.status_code in {200, 201}:
            return response.json()  # type: ignore[no-any-return]

        logger.warning(
            "Search service returned non-2xx on upload",
            extra={"status_code": response.status_code},
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unexpected response from search service",
        )
    except HTTPException:
        raise
    except httpx.ConnectError as err:
        logger.warning("Search service unavailable", extra={"url": url})
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Search service is currently unavailable",
        ) from err
    except Exception as err:
        logger.exception("Unexpected error proxying file upload to search service")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Error communicating with search service",
        ) from err


@router.get("/documents", summary="List indexed documents")
async def list_documents(current_user: CurrentUser) -> dict[str, Any]:
    """
    Proxy to the search service to retrieve the list of indexed documents.

    Args:
        current_user: Authenticated CRM user (injected by FastAPI DI).

    Returns:
        The parsed JSON response, or an empty dict if the service is unavailable.
    """
    return await _proxy_get("/api/v1/documents")


@router.get("/documents/{document_id}", summary="Get document detail")
async def get_document(
    document_id: UUID,
    current_user: CurrentUser,
) -> dict[str, Any]:
    """
    Proxy to the search service to retrieve metadata for a single document.

    Args:
        document_id: UUID of the document to retrieve.
        current_user: Authenticated CRM user (injected by FastAPI DI).

    Returns:
        The parsed JSON response, or an empty dict if the service is unavailable.
    """
    return await _proxy_get(f"/api/v1/documents/{document_id}")


@router.delete("/documents/{document_id}", summary="Delete an indexed document")
async def delete_document(
    document_id: UUID,
    current_user: CurrentUser,
) -> dict[str, Any]:
    """
    Proxy a DELETE request to the search service to remove a document and its vectors.

    Args:
        document_id: UUID of the document to delete.
        current_user: Authenticated CRM user (injected by FastAPI DI).

    Returns:
        The parsed JSON confirmation response from the search service.

    Raises:
        HTTPException: 404 if the document does not exist,
            503 if the search service is unreachable.
    """
    return await _proxy_delete(f"/api/v1/documents/{document_id}")


@router.post("/query", summary="Run a semantic search query")
async def query(
    current_user: CurrentUser,
    body: dict[str, Any],
) -> dict[str, Any]:
    """
    Proxy a semantic search query to the search service.

    The request body is forwarded verbatim as JSON.  The search service is
    responsible for embedding the query string and returning ranked results.

    Args:
        current_user: Authenticated CRM user (injected by FastAPI DI).
        body: Arbitrary JSON body forwarded to the search service
              (typically ``{"query": "...", "top_k": 5}``).

    Returns:
        The parsed JSON response with ranked document matches.

    Raises:
        HTTPException: 503 if the search service is unreachable,
            502 on any other upstream error.
    """
    url = _build_url("/api/v1/query")
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
            response = await client.post(url, json=body)

        if response.status_code == 200:
            return response.json()  # type: ignore[no-any-return]

        logger.warning(
            "Search service returned non-200 on query",
            extra={"status_code": response.status_code},
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unexpected response from search service",
        )
    except HTTPException:
        raise
    except httpx.ConnectError as err:
        logger.warning("Search service unavailable", extra={"url": url})
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Search service is currently unavailable",
        ) from err
    except Exception as err:
        logger.exception("Unexpected error proxying query to search service")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Error communicating with search service",
        ) from err


@router.get("/health", summary="Health check of the search service")
async def health(current_user: CurrentUser) -> dict[str, Any]:
    """
    Proxy a health check request to the search service.

    Useful for the CRM dashboard to display the availability status of the
    semantic search feature without exposing the internal service address.

    Args:
        current_user: Authenticated CRM user (injected by FastAPI DI).

    Returns:
        The parsed JSON health response, or ``{"status": "unavailable"}`` if
        the service cannot be reached.
    """
    url = _build_url("/api/v1/health")
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
            response = await client.get(url)

        if response.status_code == 200:
            return response.json()  # type: ignore[no-any-return]

        logger.warning(
            "Search service health check returned non-200",
            extra={"status_code": response.status_code},
        )
    except httpx.ConnectError:
        logger.warning("Search service unavailable during health check", extra={"url": url})
    except Exception:
        logger.exception("Unexpected error during search service health check")

    return {"status": "unavailable"}
