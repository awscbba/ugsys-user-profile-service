"""Exploratory + fix-checking tests for SecurityHeadersMiddleware.

Phase 1 tests (1.1.x, 1.2) run on UNFIXED code and are expected to FAIL.
Phase 3 tests (3.1.x, 3.2) run on FIXED code and are expected to PASS.
Phase 4 tests (4.1-4.3) verify preservation of already-correct headers.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from hypothesis import given
from hypothesis import settings as hyp_settings
from hypothesis import strategies as st

from src.presentation.middleware.security_headers import SecurityHeadersMiddleware


def make_app(path: str = "/test") -> FastAPI:
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)

    @app.get(path)
    async def endpoint() -> dict:
        return {"ok": True}

    return app


def make_api_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)

    @app.get("/api/v1/profiles/me")
    async def api_endpoint() -> dict:
        return {"ok": True}

    @app.get("/health")
    async def health_endpoint() -> dict:
        return {"ok": True}

    return app


# ── Phase 1: Exploratory tests (expected to FAIL on unfixed code) ─────────────


class TestSecurityHeadersExploratory:
    """1.1.x — These tests FAIL on unfixed code to confirm bugs exist."""

    def test_1_1_1_xss_protection_should_be_zero(self):
        """1.1.1 Assert X-XSS-Protection: 0 (will fail — current value is '1; mode=block')."""
        client = TestClient(make_app())
        response = client.get("/test")
        assert response.headers.get("x-xss-protection") == "0", (
            f"Expected '0', got '{response.headers.get('x-xss-protection')}'"
        )

    def test_1_1_2_hsts_should_contain_preload(self):
        """1.1.2 Assert HSTS contains 'preload' (will fail — missing directive)."""
        client = TestClient(make_app())
        response = client.get("/test")
        hsts = response.headers.get("strict-transport-security", "")
        assert "preload" in hsts, f"Expected 'preload' in HSTS, got: '{hsts}'"

    def test_1_1_3_csp_should_be_none_frame_ancestors(self):
        """1.1.3 Assert CSP is 'default-src 'none'; frame-ancestors 'none'' (will fail)."""
        client = TestClient(make_app())
        response = client.get("/test")
        csp = response.headers.get("content-security-policy", "")
        assert "default-src 'none'" in csp, f"Expected 'default-src 'none'' in CSP, got: '{csp}'"
        assert "frame-ancestors 'none'" in csp, (
            f"Expected 'frame-ancestors 'none'' in CSP, got: '{csp}'"
        )

    def test_1_1_4_permissions_policy_should_be_present(self):
        """1.1.4 Assert Permissions-Policy header present (will fail — missing)."""
        client = TestClient(make_app())
        response = client.get("/test")
        assert "permissions-policy" in response.headers, "Expected Permissions-Policy header"

    def test_1_1_5_cross_origin_opener_policy_should_be_present(self):
        """1.1.5 Assert Cross-Origin-Opener-Policy header present (will fail — missing)."""
        client = TestClient(make_app())
        response = client.get("/test")
        assert "cross-origin-opener-policy" in response.headers, (
            "Expected Cross-Origin-Opener-Policy header"
        )

    def test_1_1_6_cross_origin_resource_policy_should_be_present(self):
        """1.1.6 Assert Cross-Origin-Resource-Policy header present (will fail — missing)."""
        client = TestClient(make_app())
        response = client.get("/test")
        assert "cross-origin-resource-policy" in response.headers, (
            "Expected Cross-Origin-Resource-Policy header"
        )

    def test_1_1_7_server_header_should_be_absent(self):
        """1.1.7 Assert 'server' header absent (will fail — currently exposed)."""
        client = TestClient(make_app())
        response = client.get("/test")
        assert "server" not in response.headers, (
            f"Expected 'server' header to be absent, got: '{response.headers.get('server')}'"
        )

    def test_1_1_8_cache_control_on_api_path(self):
        """1.1.8 Assert Cache-Control present on /api/* paths (will fail — missing)."""
        client = TestClient(make_api_app())
        response = client.get("/api/v1/profiles/me")
        assert "cache-control" in response.headers, "Expected Cache-Control header on /api/* path"
        assert response.headers["cache-control"] == "no-store, no-cache, must-revalidate"

    def test_1_1_9_middleware_uses_private_attribute(self):
        """1.1.9 Assert middleware uses _SECURITY_HEADERS (private) not SECURITY_HEADERS (public)."""  # noqa: E501
        import src.presentation.middleware.security_headers as mod

        assert hasattr(mod, "_SECURITY_HEADERS"), (
            "Expected _SECURITY_HEADERS module-level attribute"
        )
        assert not hasattr(mod, "SECURITY_HEADERS"), (
            "Expected SECURITY_HEADERS to be renamed to _SECURITY_HEADERS"
        )


# ── Phase 1: PBT (1.2) — Cache-Control path property test ────────────────────


class TestCacheControlPathPropertyExploratory:
    """1.2 PBT: Cache-Control present iff path starts with /api/ (FAILS on unfixed code).

    **Validates: Requirements 2.5**
    """

    @given(
        path_suffix=st.text(
            alphabet=st.characters(
                whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="/-_"
            ),
            min_size=1,
            max_size=30,
        )
    )
    @hyp_settings(max_examples=20)
    def test_1_2_cache_control_iff_api_path(self, path_suffix: str) -> None:
        """For any HTTP path, Cache-Control is present iff path starts with /api/."""
        # Build two apps: one with /api/ prefix, one without
        api_path = f"/api/{path_suffix.lstrip('/')}"
        non_api_path = f"/other/{path_suffix.lstrip('/')}"

        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware)

        @app.get(api_path)
        async def api_ep() -> dict:
            return {}

        @app.get(non_api_path)
        async def non_api_ep() -> dict:
            return {}

        client = TestClient(app)

        # /api/* paths MUST have Cache-Control
        api_resp = client.get(api_path)
        assert "cache-control" in api_resp.headers, f"Expected Cache-Control on {api_path}"

        # Non-/api/ paths MUST NOT have Cache-Control
        non_api_resp = client.get(non_api_path)
        assert "cache-control" not in non_api_resp.headers, (
            f"Expected NO Cache-Control on {non_api_path}"
        )


# ── Phase 3: Fix-checking tests (expected to PASS on fixed code) ──────────────


class TestSecurityHeadersFixed:
    """3.1.x — These tests PASS on fixed code."""

    def test_3_1_1_all_9_required_headers_present(self):
        """3.1.1 Assert all 9 required headers present with exact values."""
        client = TestClient(make_app())
        response = client.get("/test")
        h = response.headers

        assert h.get("x-content-type-options") == "nosniff"
        assert h.get("x-frame-options") == "DENY"
        assert h.get("x-xss-protection") == "0"
        assert h.get("strict-transport-security") == "max-age=31536000; includeSubDomains; preload"
        assert "default-src 'none'" in h.get("content-security-policy", "")
        assert "frame-ancestors 'none'" in h.get("content-security-policy", "")
        assert h.get("referrer-policy") == "strict-origin-when-cross-origin"
        assert "camera=()" in h.get("permissions-policy", "")
        assert h.get("cross-origin-opener-policy") == "same-origin"
        # cross-origin allows the SPA (different origin) to read API responses
        assert h.get("cross-origin-resource-policy") == "cross-origin"

    def test_3_1_5_options_preflight_skips_security_headers(self):
        """3.1.5 Assert OPTIONS requests are passed through without security headers.

        Cross-Origin-Resource-Policy: same-origin on a preflight response would
        cause browsers to reject it with a CORS error.
        """
        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware)

        @app.options("/api/v1/profiles/me")
        async def options_ep() -> dict:
            return {}

        client = TestClient(app)
        response = client.options("/api/v1/profiles/me")
        assert "cross-origin-resource-policy" not in response.headers
        assert "x-frame-options" not in response.headers

    def test_3_1_2_server_header_absent(self):
        """3.1.2 Assert server header absent from responses."""
        client = TestClient(make_app())
        response = client.get("/test")
        assert "server" not in response.headers

    def test_3_1_3_cache_control_on_api_path_and_absent_on_non_api(self):
        """3.1.3 Assert Cache-Control present on /api/* and absent on non-/api/ paths."""
        client = TestClient(make_api_app())

        api_resp = client.get("/api/v1/profiles/me")
        assert api_resp.headers.get("cache-control") == "no-store, no-cache, must-revalidate"

        health_resp = client.get("/health")
        assert "cache-control" not in health_resp.headers

    def test_3_1_4_middleware_uses_private_attribute(self):
        """3.1.4 Assert middleware attribute is _SECURITY_HEADERS (private)."""
        import src.presentation.middleware.security_headers as mod

        assert hasattr(mod, "_SECURITY_HEADERS"), (
            "Expected _SECURITY_HEADERS module-level attribute"
        )
        assert not hasattr(mod, "SECURITY_HEADERS"), "Expected SECURITY_HEADERS to be removed"


# ── Phase 3: PBT (3.2) — Cache-Control path property test on fixed code ──────


class TestCacheControlPathPropertyFixed:
    """3.2 PBT: Cache-Control present iff path starts with /api/ (PASSES on fixed code).

    **Validates: Requirements 2.5**
    """

    @given(
        path_suffix=st.text(
            alphabet=st.characters(
                whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="/-_"
            ),
            min_size=1,
            max_size=30,
        )
    )
    @hyp_settings(max_examples=20)
    def test_3_2_cache_control_iff_api_path(self, path_suffix: str) -> None:
        """For any HTTP path, Cache-Control is present iff path starts with /api/."""
        api_path = f"/api/{path_suffix.lstrip('/')}"
        non_api_path = f"/other/{path_suffix.lstrip('/')}"

        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware)

        @app.get(api_path)
        async def api_ep() -> dict:
            return {}

        @app.get(non_api_path)
        async def non_api_ep() -> dict:
            return {}

        client = TestClient(app)

        api_resp = client.get(api_path)
        assert "cache-control" in api_resp.headers

        non_api_resp = client.get(non_api_path)
        assert "cache-control" not in non_api_resp.headers


# ── Phase 4: Preservation tests ───────────────────────────────────────────────


class TestSecurityHeadersPreservation:
    """4.1-4.3 — Verify already-correct headers are unchanged after fix."""

    def test_4_1_x_content_type_options_unchanged(self):
        """4.1 Assert X-Content-Type-Options: nosniff unchanged."""
        client = TestClient(make_app())
        response = client.get("/test")
        assert response.headers.get("x-content-type-options") == "nosniff"

    def test_4_2_x_frame_options_unchanged(self):
        """4.2 Assert X-Frame-Options: DENY unchanged."""
        client = TestClient(make_app())
        response = client.get("/test")
        assert response.headers.get("x-frame-options") == "DENY"

    def test_4_3_referrer_policy_unchanged(self):
        """4.3 Assert Referrer-Policy: strict-origin-when-cross-origin unchanged."""
        client = TestClient(make_app())
        response = client.get("/test")
        assert response.headers.get("referrer-policy") == "strict-origin-when-cross-origin"
