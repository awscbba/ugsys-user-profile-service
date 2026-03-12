"""Rate limiting middleware — per-user (JWT sub) with 3 windows + response headers."""

import base64
import json
import time
from collections import defaultdict
from collections.abc import Awaitable, Callable
from math import ceil

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

# Window durations (seconds)
_WINDOW_MINUTE: float = 60.0
_WINDOW_HOUR: float = 3600.0
_BURST_WINDOW: float = 1.0

# Limits per window
_MAX_PER_MINUTE: int = 60
_MAX_PER_HOUR: int = 1000
_MAX_BURST: int = 10


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: object, rate_limit: int = _MAX_PER_MINUTE) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self._rate_limit = rate_limit
        self._counters: dict[str, list[float]] = defaultdict(list)

    def _extract_key(self, request: Request) -> str:
        """Extract rate-limit key: JWT sub → 'user:{sub}', fallback → 'ip:{ip}'."""
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[len("Bearer ") :]
            try:
                parts = token.split(".")
                if len(parts) >= 2:
                    # Decode payload without signature verification
                    padded = parts[1] + "=" * (-len(parts[1]) % 4)
                    payload = json.loads(base64.urlsafe_b64decode(padded))
                    sub = payload.get("sub")
                    if sub:
                        return f"user:{sub}"
            except Exception:  # noqa: S110
                pass
        # Fallback to IP
        client_host = request.client.host if request.client else "unknown"
        ip = request.headers.get("X-Forwarded-For", client_host).split(",")[0].strip()
        return f"ip:{ip}"

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # Pass OPTIONS preflight requests straight through — rate limiting them
        # causes the CORS allow_credentials header to be dropped, resulting in
        # a preflight failure ("does not have HTTP ok status").
        if request.method == "OPTIONS":
            return await call_next(request)

        key = self._extract_key(request)
        now = time.time()

        # Prune timestamps older than 1 hour (the longest window)
        self._counters[key] = [t for t in self._counters[key] if t > now - _WINDOW_HOUR]

        timestamps = self._counters[key]

        # Count hits in each window
        burst_count = sum(1 for t in timestamps if t > now - _BURST_WINDOW)
        minute_count = sum(1 for t in timestamps if t > now - _WINDOW_MINUTE)
        hour_count = len(timestamps)

        # Check limits (use self._rate_limit for per-minute to allow test overrides)
        per_minute_limit = self._rate_limit
        if (
            burst_count >= _MAX_BURST
            or minute_count >= per_minute_limit
            or hour_count >= _MAX_PER_HOUR
        ):
            retry_after = ceil(
                _WINDOW_MINUTE - (now - min(timestamps)) if timestamps else _WINDOW_MINUTE
            )
            return JSONResponse(
                {"detail": "Rate limit exceeded"},
                status_code=429,
                headers={"Retry-After": str(max(1, retry_after))},
            )

        # Record this request
        self._counters[key].append(now)
        minute_count += 1

        response = await call_next(request)

        # Add rate-limit headers on non-429 responses
        remaining = max(0, per_minute_limit - minute_count)
        reset_at = ceil(now + _WINDOW_MINUTE)
        response.headers["X-RateLimit-Limit"] = str(per_minute_limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_at)
        return response
