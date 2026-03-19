"""Unit and property-based tests for GET /plugin-manifest.json.

Feature: ups-plugin-manifest
"""

import json

import jsonschema
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from hypothesis import given
from hypothesis import settings as hyp_settings
from hypothesis import strategies as st

from src.presentation.api.v1.plugin_manifest import router


def _make_app() -> FastAPI:
    """Minimal app with only the plugin_manifest router — no JWT wiring needed."""
    app = FastAPI()
    app.include_router(router)
    return app


_app = _make_app()

# ── Schema (copied from ugsys-admin-panel manifest_validator.py) ──────────────

PLUGIN_MANIFEST_SCHEMA: dict = {
    "type": "object",
    "required": ["name", "version", "entryPoint", "routes", "navigation"],
    "properties": {
        "name": {"type": "string", "minLength": 1},
        "version": {"type": "string", "pattern": r"^\d+\.\d+\.\d+$"},
        "entryPoint": {"type": "string", "format": "uri"},
        "healthEndpoint": {"type": "string"},
        "stylesheetUrl": {"type": "string", "format": "uri"},
        "configSchema": {"type": "object"},
        "requiredPermissions": {"type": "array", "items": {"type": "string"}},
        "routes": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["path", "requiredRoles", "label"],
                "properties": {
                    "path": {"type": "string"},
                    "label": {"type": "string"},
                    "requiredRoles": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
        "navigation": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["label", "icon", "path", "requiredRoles"],
                "properties": {
                    "label": {"type": "string"},
                    "icon": {"type": "string"},
                    "path": {"type": "string"},
                    "group": {"type": "string"},
                    "order": {"type": "integer"},
                    "requiredRoles": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
    },
}

_VALID_PLATFORM_ROLES = {
    "super_admin",
    "admin",
    "moderator",
    "auditor",
    "member",
    "guest",
    "system",
}

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(_app)


@pytest.fixture(scope="module")
def manifest(client: TestClient) -> dict:
    response = client.get("/plugin-manifest.json")
    return response.json()


# ── Unit tests ────────────────────────────────────────────────────────────────


def test_returns_200_without_auth(client: TestClient) -> None:
    """GET /plugin-manifest.json without Authorization header → HTTP 200."""
    response = client.get("/plugin-manifest.json")
    assert response.status_code == 200


def test_content_type_is_json(client: TestClient) -> None:
    """Response Content-Type must be application/json."""
    response = client.get("/plugin-manifest.json")
    assert "application/json" in response.headers["content-type"]


def test_body_passes_schema(manifest: dict) -> None:
    """Response body must pass PLUGIN_MANIFEST_SCHEMA without errors."""
    jsonschema.validate(manifest, PLUGIN_MANIFEST_SCHEMA)


def test_required_top_level_fields_present(manifest: dict) -> None:
    """Response body must contain all required top-level fields."""
    for field in ("name", "version", "entryPoint", "routes", "navigation"):
        assert field in manifest, f"Missing required field: {field}"


def test_name_and_health_endpoint(manifest: dict) -> None:
    """name must be 'user-profile-service' and healthEndpoint must be '/health'."""
    assert manifest["name"] == "user-profile-service"
    assert manifest.get("healthEndpoint") == "/health"


def test_no_moderator_in_required_roles(manifest: dict) -> None:
    """No requiredRoles array in the manifest may contain 'moderator'."""
    for route in manifest.get("routes", []):
        assert "moderator" not in route.get("requiredRoles", []), (
            f"Route {route['path']} contains 'moderator' in requiredRoles"
        )
    for nav in manifest.get("navigation", []):
        assert "moderator" not in nav.get("requiredRoles", []), (
            f"Nav entry {nav['path']} contains 'moderator' in requiredRoles"
        )


def test_users_route_exists(manifest: dict) -> None:
    """Route entry for /app/user-profile-service/users exists with correct roles."""
    routes = manifest.get("routes", [])
    path = "/app/user-profile-service/users"
    users_route = next((r for r in routes if r["path"] == path), None)
    assert users_route is not None, f"No route with path '{path}' found"
    assert users_route["label"] == "Users"
    assert "admin" in users_route["requiredRoles"]


def test_users_navigation_entry(manifest: dict) -> None:
    """Navigation entry for /app/user-profile-service/users has correct fields."""
    nav = manifest.get("navigation", [])
    path = "/app/user-profile-service/users"
    entry = next((n for n in nav if n["path"] == path), None)
    assert entry is not None, f"No navigation entry with path '{path}' found"
    assert entry["label"] == "Users"
    assert entry["icon"] == "👤"
    assert entry["group"] == "Users"
    assert entry["order"] == 1
    assert "admin" in entry["requiredRoles"]


def test_no_projects_path_in_manifest(manifest: dict) -> None:
    """Scope boundary: no route or nav entry may have path '/projects'."""
    for route in manifest.get("routes", []):
        assert route["path"] != "/projects", "Found /projects route — out of scope"
    for nav in manifest.get("navigation", []):
        assert nav["path"] != "/projects", "Found /projects nav entry — out of scope"


# ── Property-based tests ──────────────────────────────────────────────────────


@given(st.just(_app))
@hyp_settings(max_examples=100)
def test_manifest_passes_schema(_app_: object) -> None:
    """Feature: ups-plugin-manifest, Property 1: For any invocation of GET /plugin-manifest.json,
    the parsed response body must pass the PLUGIN_MANIFEST_SCHEMA validator without errors.
    Validates: Requirements 1.4, 5.1
    """
    response = TestClient(_app_).get("/plugin-manifest.json")  # type: ignore[arg-type]
    manifest = response.json()
    jsonschema.validate(manifest, PLUGIN_MANIFEST_SCHEMA)


@given(st.just(_app))
@hyp_settings(max_examples=100)
def test_manifest_json_round_trip(_app_: object) -> None:
    """Feature: ups-plugin-manifest, Property 2: For any invocation of GET /plugin-manifest.json,
    serialising the parsed response body to JSON and parsing it back must produce a document
    equal to the original.
    Validates: Requirements 1.3, 5.2
    """
    response = TestClient(_app_).get("/plugin-manifest.json")  # type: ignore[arg-type]
    manifest = response.json()
    assert json.loads(json.dumps(manifest)) == manifest


def _get_manifest_once() -> dict:
    return TestClient(_app).get("/plugin-manifest.json").json()


@given(
    st.sampled_from(
        [r["path"] for r in _get_manifest_once()["routes"]]
        + [n["path"] for n in _get_manifest_once()["navigation"]]
    )
)
@hyp_settings(max_examples=100)
def test_all_paths_start_with_slash(path: str) -> None:
    """Feature: ups-plugin-manifest, Property 3: For any RouteDescriptor in routes and any
    NavigationEntry in navigation, the path field must satisfy path.startswith("/").
    Validates: Requirements 3.2, 4.4, 5.3, 6.7
    """
    assert path.startswith("/"), f"Path '{path}' does not start with '/'"


@given(st.sampled_from(_get_manifest_once()["navigation"]))
@hyp_settings(max_examples=100)
def test_navigation_fields_non_empty(entry: dict) -> None:
    """Feature: ups-plugin-manifest, Property 4: For any NavigationEntry in navigation,
    the label, icon, and path fields must each be non-empty strings.
    Validates: Requirements 4.2, 4.3, 4.4, 5.4, 6.10
    """
    assert len(entry["label"]) > 0
    assert len(entry["icon"]) > 0
    assert len(entry["path"]) > 0


def _all_roles() -> list[str]:
    m = _get_manifest_once()
    roles: list[str] = []
    for r in m.get("routes", []):
        roles.extend(r.get("requiredRoles", []))
    for n in m.get("navigation", []):
        roles.extend(n.get("requiredRoles", []))
    return roles


@given(st.sampled_from(_all_roles()))
@hyp_settings(max_examples=100)
def test_all_roles_are_valid_platform_roles(role: str) -> None:
    """Feature: ups-plugin-manifest, Property 5: For any role string in any requiredRoles array
    within routes or navigation, the value must be a member of the valid Platform_Role set.
    Validates: Requirements 3.3, 4.5, 5.5, 6.8
    """
    assert role in _VALID_PLATFORM_ROLES, f"Role '{role}' is not a valid Platform_Role"


@given(st.sampled_from(_all_roles()))
@hyp_settings(max_examples=100)
def test_no_moderator_in_required_roles_pbt(role: str) -> None:
    """Feature: ups-plugin-manifest, Property 6: For any role string in any requiredRoles array
    within the manifest, the value must not equal 'moderator'.
    Validates: Requirements 3.5, 4.7, 5.6, 6.6
    """
    assert role != "moderator", "Found 'moderator' in requiredRoles — admin-only invariant violated"
