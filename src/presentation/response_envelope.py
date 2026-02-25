"""Response envelope utilities for consistent API response formatting.

Provides `success_response` for single-item responses and `list_response`
for paginated collection responses, both wrapping data with metadata.
"""

from math import ceil
from typing import Any


def success_response(data: object, request_id: str = "") -> dict[str, Any]:
    """Wrap a single data payload in the standard success envelope.

    Args:
        data: The response payload to wrap.
        request_id: The correlation/request ID from the incoming request.

    Returns:
        Envelope dict with ``data`` and ``meta.request_id``.
    """
    return {
        "data": data,
        "meta": {
            "request_id": request_id,
        },
    }


def list_response(
    data: list[Any],
    total: int,
    page: int,
    page_size: int,
    request_id: str = "",
) -> dict[str, Any]:
    """Wrap a paginated list payload in the standard list envelope.

    Args:
        data: The page of items to wrap.
        total: Total number of items across all pages.
        page: Current page number (1-based).
        page_size: Number of items per page.
        request_id: The correlation/request ID from the incoming request.

    Returns:
        Envelope dict with ``data`` and ``meta`` containing pagination info.
    """
    total_pages = ceil(total / page_size) if page_size > 0 else 0
    return {
        "data": data,
        "meta": {
            "request_id": request_id,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        },
    }
