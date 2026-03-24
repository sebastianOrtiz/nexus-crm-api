"""
Domain exceptions used throughout the service layer.

Keeping exceptions in one place prevents scattered ``raise HTTPException``
calls inside business logic and makes the service layer framework-agnostic.
The API routers translate these into the appropriate HTTP responses.
"""


class NexusCRMError(Exception):
    """Base class for all application-specific errors."""


class NotFoundError(NexusCRMError):
    """Raised when a requested resource does not exist in the tenant scope."""

    def __init__(self, resource: str, resource_id: str | None = None) -> None:
        detail = f"{resource} not found"
        if resource_id:
            detail = f"{resource} '{resource_id}' not found"
        super().__init__(detail)
        self.resource = resource
        self.resource_id = resource_id


class ForbiddenError(NexusCRMError):
    """Raised when the current user lacks permission to perform an action."""

    def __init__(self, detail: str = "You do not have permission to perform this action") -> None:
        super().__init__(detail)


class ConflictError(NexusCRMError):
    """Raised when creating a resource would violate a uniqueness constraint."""

    def __init__(self, detail: str) -> None:
        super().__init__(detail)


class UnauthorizedError(NexusCRMError):
    """Raised when authentication credentials are missing or invalid."""

    def __init__(self, detail: str = "Could not validate credentials") -> None:
        super().__init__(detail)


class ValidationError(NexusCRMError):
    """Raised when business-level validation fails (beyond Pydantic schema validation)."""

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
