"""Rate limiting middleware — 60 req/min per user (in-memory, Lambda-safe)."""

import time
from collections import defaultdict
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

RATE_LIMIT = 60
WINDOW_SECONDS = 60


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: object, rate_limit: int = RATE_LIMIT) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self._rate_limit = rate_limit
        self._counters: dict[str, list[float]] = defaultdict(list)

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        client_host = request.client.host if request.client else "unknown"
        client = request.headers.get("X-Forwarded-For", client_host)
        now = time.time()
        window_start = now - WINDOW_SECONDS
        hits = self._counters[client]
        self._counters[client] = [t for t in hits if t > window_start]
        if len(self._counters[client]) >= self._rate_limit:
            return JSONResponse({"detail": "Rate limit exceeded"}, status_code=429)
        self._counters[client].append(now)
        return await call_next(request)
