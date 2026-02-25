"""Exception handlers for ugsys-user-profile-service.

Translates domain exceptions into HTTP responses with safe user-facing messages.
Internal details are logged only — never exposed to API callers.
"""

import structlog
from fastapi import Request
from fastapi.responses import JSONResponse

from src.domain.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    DomainError,
    ExternalServiceError,
    NotFoundError,
    RepositoryError,
    ValidationError,
)

logger = structlog.get_logger()

_STATUS_MAP: dict[type[DomainError], int] = {
    ValidationError: 422,
    NotFoundError: 404,
    ConflictError: 409,
    AuthorizationError: 403,
    AuthenticationError: 401,
    RepositoryError: 500,
    ExternalServiceError: 502,
}


async def domain_exception_handler(request: Request, exc: DomainError) -> JSONResponse:
    """Handle known domain exceptions and return structured error responses."""
    status = _STATUS_MAP.get(type(exc), 500)
    logger.error(
        "domain_error",
        error_code=exc.error_code,
        message=exc.message,
        status=status,
        path=request.url.path,
    )
    return JSONResponse(
        status_code=status,
        content={
            "error": {
                "code": exc.error_code,
                "message": exc.user_message,
            },
            "meta": {
                "request_id": request.headers.get("X-Request-ID", ""),
            },
        },
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions and return a generic 500 response."""
    logger.error(
        "unhandled_exception",
        error=str(exc),
        path=request.url.path,
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
            },
            "meta": {
                "request_id": request.headers.get("X-Request-ID", ""),
            },
        },
    )
