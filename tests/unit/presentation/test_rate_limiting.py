"""Exploratory + fix-checking + preservation tests for RateLimitMiddleware.

Phase 1 (1.6.x, 1.7): run on UNFIXED code — expected to FAIL.
Phase 3 (3.6.x, 3.7): run on FIXED code — expected to PASS.
"""

from __future__ import annotations

import base64
import json
import time
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from hypothesis import given
from hypothesis import settings as hyp_settings
from hypothesis import strategies as st

from src.presentation.middleware.rate_limiting import RateLimitMiddleware

# ── Helpers ───────────────────────────────────────────────────────────────────


def make_jwt(sub: str) -> str:
    """Build a minimal unsigned JWT with the given sub claim."""
    header = base64.urlsafe_b64encode(b'{"alg":"none"}').rstrip(b"=").decode()
    payload = (
        base64.urlsafe_b64encode(json.dumps({"sub": sub, "exp": 9999999999}).encode())
        .rstrip(b"=")
        .decode()
    )
    return f"{header}.{payload}."


def make_app(rate_limit: int = 60) -> FastAPI:
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, rate_limit=rate_limit)

    @app.get("/test")
    async def endpoint() -> dict:
        return {"ok": True}

    return app


# ── Phase 1: Exploratory tests (expected to FAIL on unfixed code) ─────────────


class TestRateLimitingExploratory:
    """1.6.x — These tests FAIL on unfixed code to confirm bugs exist."""

    def test_1_6_1_same_sub_different_ips_share_counter(self):
        """1.6.1 Two requests with same JWT sub from different IPs share a counter."""
        app = make_app(rate_limit=1)
        client = TestClient(app, raise_server_exceptions=False)
        jwt = make_jwt("user-abc")
        auth = {"Authorization": f"Bearer {jwt}"}

        # First request from IP 1 — should succeed
        r1 = client.get("/test", headers={**auth, "X-Forwarded-For": "1.2.3.4"})
        assert r1.status_code == 200

        # Second request from different IP but same sub — should be rate-limited
        r2 = client.get("/test", headers={**auth, "X-Forwarded-For": "5.6.7.8"})
        assert r2.status_code == 429, (
            "Expected 429 — same sub from different IP should share counter"
        )

    def test_1_6_2_burst_window_enforced(self):
        """1.6.2 11 requests in 1 second → 429 (burst limit = 10)."""
        app = make_app()
        client = TestClient(app, raise_server_exceptions=False)
        jwt = make_jwt("burst-user")
        auth = {"Authorization": f"Bearer {jwt}"}

        now = time.time()
        with patch("src.presentation.middleware.rate_limiting.time") as mock_time:
            mock_time.time.return_value = now
            responses = [client.get("/test", headers=auth) for _ in range(11)]

        status_codes = [r.status_code for r in responses]
        assert 429 in status_codes, (
            f"Expected 429 after 11 requests in 1s (burst limit), got: {status_codes}"
        )

    def test_1_6_3_hour_window_enforced(self):
        """1.6.3 1001 requests in 1 hour → 429 (hour limit = 1000)."""
        app = make_app()
        client = TestClient(app, raise_server_exceptions=False)
        jwt = make_jwt("hour-user")
        auth = {"Authorization": f"Bearer {jwt}"}

        now = time.time()
        responses = []
        with patch("src.presentation.middleware.rate_limiting.time") as mock_time:
            for i in range(1001):
                mock_time.time.return_value = now - 3600 + (i * 3.5)
                r = client.get("/test", headers=auth)
                responses.append(r.status_code)

        assert 429 in responses, (
            f"Expected 429 after 1001 requests in 1 hour, last few: {responses[-5:]}"
        )

    def test_1_6_4_x_ratelimit_limit_present_on_200(self):
        """1.6.4 Assert X-RateLimit-Limit present on 200 response."""
        client = TestClient(make_app())
        response = client.get("/test")
        assert "x-ratelimit-limit" in response.headers, (
            "Expected X-RateLimit-Limit header on 200 response"
        )

    def test_1_6_5_x_ratelimit_remaining_present_on_200(self):
        """1.6.5 Assert X-RateLimit-Remaining present on 200 response."""
        client = TestClient(make_app())
        response = client.get("/test")
        assert "x-ratelimit-remaining" in response.headers, (
            "Expected X-RateLimit-Remaining header on 200 response"
        )

    def test_1_6_6_x_ratelimit_reset_present_on_200(self):
        """1.6.6 Assert X-RateLimit-Reset present on 200 response."""
        client = TestClient(make_app())
        response = client.get("/test")
        assert "x-ratelimit-reset" in response.headers, (
            "Expected X-RateLimit-Reset header on 200 response"
        )

    def test_1_6_7_retry_after_present_on_429(self):
        """1.6.7 Exceed rate limit — assert Retry-After present on 429 response."""
        app = make_app(rate_limit=1)
        client = TestClient(app, raise_server_exceptions=False)
        client.get("/test")  # consume the 1 allowed request
        response = client.get("/test")
        assert response.status_code == 429
        assert "retry-after" in response.headers, "Expected Retry-After header on 429 response"


# ── Phase 1: PBT (1.7) ────────────────────────────────────────────────────────


class TestSubIsolationPBTExploratory:
    """1.7 PBT: Two distinct JWT sub values have independent counters (FAILS on unfixed code).

    **Validates: Requirements 2.12, 2.13**
    """

    @given(
        sub1=st.text(
            min_size=5,
            max_size=20,
            alphabet=st.characters(whitelist_categories=("Ll", "Nd"), whitelist_characters="-"),
        ),
        sub2=st.text(
            min_size=5,
            max_size=20,
            alphabet=st.characters(whitelist_categories=("Ll", "Nd"), whitelist_characters="-"),
        ),
    )
    @hyp_settings(max_examples=5)
    def test_1_7_different_subs_have_independent_counters(self, sub1: str, sub2: str) -> None:
        """Two distinct JWT sub values should have independent rate limit counters."""
        if sub1 == sub2:
            return  # skip equal subs

        app = make_app(rate_limit=1)
        client = TestClient(app, raise_server_exceptions=False)

        jwt1 = make_jwt(sub1)
        jwt2 = make_jwt(sub2)

        # Exhaust sub1's limit
        client.get("/test", headers={"Authorization": f"Bearer {jwt1}"})
        r1_blocked = client.get("/test", headers={"Authorization": f"Bearer {jwt1}"})
        assert r1_blocked.status_code == 429

        # sub2 should still be allowed (independent counter)
        r2 = client.get("/test", headers={"Authorization": f"Bearer {jwt2}"})
        assert r2.status_code == 200, f"Expected sub2 ({sub2}) to be independent from sub1 ({sub1})"


# ── Phase 3: Fix-checking tests (expected to PASS on fixed code) ──────────────


class TestRateLimitingFixed:
    """3.6.x — These tests PASS on fixed code."""

    def test_3_6_1_same_sub_different_ips_share_counter(self):
        """3.6.1 Two requests with same JWT sub from different IPs share a counter."""
        app = make_app(rate_limit=1)
        client = TestClient(app, raise_server_exceptions=False)
        jwt = make_jwt("user-abc")
        auth = {"Authorization": f"Bearer {jwt}"}

        r1 = client.get("/test", headers={**auth, "X-Forwarded-For": "1.2.3.4"})
        assert r1.status_code == 200

        r2 = client.get("/test", headers={**auth, "X-Forwarded-For": "5.6.7.8"})
        assert r2.status_code == 429

    def test_3_6_2_burst_window_enforced(self):
        """3.6.2 11 requests in 1 second → 429."""
        app = make_app()
        client = TestClient(app, raise_server_exceptions=False)
        jwt = make_jwt("burst-user")
        auth = {"Authorization": f"Bearer {jwt}"}

        now = time.time()
        with patch("src.presentation.middleware.rate_limiting.time") as mock_time:
            mock_time.time.return_value = now
            responses = [client.get("/test", headers=auth) for _ in range(11)]

        assert any(r.status_code == 429 for r in responses)

    def test_3_6_3_hour_window_enforced(self):
        """3.6.3 1001 requests in 1 hour → 429."""
        app = make_app()
        client = TestClient(app, raise_server_exceptions=False)
        jwt = make_jwt("hour-user")
        auth = {"Authorization": f"Bearer {jwt}"}

        now = time.time()
        responses = []
        with patch("src.presentation.middleware.rate_limiting.time") as mock_time:
            for i in range(1001):
                mock_time.time.return_value = now - 3600 + (i * 3.5)
                r = client.get("/test", headers=auth)
                responses.append(r.status_code)

        assert 429 in responses

    def test_3_6_4_rate_limit_headers_on_non_429(self):
        """3.6.4 X-RateLimit-Limit, -Remaining, -Reset present on all non-429 responses."""
        client = TestClient(make_app())
        response = client.get("/test")
        assert response.status_code == 200
        assert "x-ratelimit-limit" in response.headers
        assert "x-ratelimit-remaining" in response.headers
        assert "x-ratelimit-reset" in response.headers

    def test_3_6_5_retry_after_on_429(self):
        """3.6.5 Retry-After present on 429 responses."""
        app = make_app(rate_limit=1)
        client = TestClient(app, raise_server_exceptions=False)
        client.get("/test")
        response = client.get("/test")
        assert response.status_code == 429
        assert "retry-after" in response.headers

    def test_3_6_6_unauthenticated_falls_back_to_ip(self):
        """3.6.6 Unauthenticated requests fall back to IP-based keying."""
        app = make_app(rate_limit=1)
        client = TestClient(app, raise_server_exceptions=False)

        # No auth header — should use IP
        r1 = client.get("/test")
        assert r1.status_code == 200

        r2 = client.get("/test")
        assert r2.status_code == 429


# ── Phase 3: PBT (3.7) ────────────────────────────────────────────────────────


class TestSubIsolationPBTFixed:
    """3.7 PBT: Two distinct JWT sub values have independent counters (PASSES on fixed code).

    **Validates: Requirements 2.12, 2.13**
    """

    @given(
        sub1=st.text(
            min_size=5,
            max_size=20,
            alphabet=st.characters(whitelist_categories=("Ll", "Nd"), whitelist_characters="-"),
        ),
        sub2=st.text(
            min_size=5,
            max_size=20,
            alphabet=st.characters(whitelist_categories=("Ll", "Nd"), whitelist_characters="-"),
        ),
    )
    @hyp_settings(max_examples=5)
    def test_3_7_different_subs_have_independent_counters(self, sub1: str, sub2: str) -> None:
        """Two distinct JWT sub values should have independent rate limit counters."""
        if sub1 == sub2:
            return

        app = make_app(rate_limit=1)
        client = TestClient(app, raise_server_exceptions=False)

        jwt1 = make_jwt(sub1)
        jwt2 = make_jwt(sub2)

        client.get("/test", headers={"Authorization": f"Bearer {jwt1}"})
        r1_blocked = client.get("/test", headers={"Authorization": f"Bearer {jwt1}"})
        assert r1_blocked.status_code == 429

        r2 = client.get("/test", headers={"Authorization": f"Bearer {jwt2}"})
        assert r2.status_code == 200
