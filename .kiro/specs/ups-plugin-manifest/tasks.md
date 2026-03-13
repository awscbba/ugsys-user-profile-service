# Implementation Plan: ups-plugin-manifest

## Overview

Add a static `GET /plugin-manifest.json` endpoint to `ugsys-user-profile-service` (presentation layer
only, no domain/infra changes) so the admin panel's BFF seed loader can fetch it, register the
service as `ACTIVE`, and populate the user management section of the sidebar navigation.

## Tasks

- [x] 1. Create `src/presentation/api/v1/plugin_manifest.py`
  - Define `router = APIRouter(tags=["Plugin Manifest"])`
  - Implement `async def get_plugin_manifest() -> dict[str, object]` decorated with `@router.get("/plugin-manifest.json")`
  - Return the hardcoded manifest dict exactly as specified in the design: `name="user-profile-service"`, `version="0.1.0"`, `entryPoint="https://profiles.apps.cloud.org.bo/assets/index-DS4a0gmi.js"`, `healthEndpoint="/health"`, `routes=[{path:"/users", label:"Users", requiredRoles:["admin","super_admin"]}]`, `navigation=[{label:"Users", icon:"👤", path:"/users", group:"Users", order:1, requiredRoles:["admin","super_admin"]}]`
  - No imports from `src.domain`, `src.application`, or `src.infrastructure` — FastAPI and stdlib only
  - _Requirements: 1.1, 1.2, 1.3, 1.7, 1.8, 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 3.1, 3.2, 3.3, 3.4, 4.1, 4.2, 4.3, 4.4_

- [x] 2. Register the router in `src/main.py`
  - Add `from src.presentation.api.v1 import plugin_manifest` to the existing v1 imports block
  - Add `app.include_router(plugin_manifest.router)` inside `create_app()`, immediately after `app.include_router(health.router)` — no prefix
  - _Requirements: 1.7_

- [x] 3. Write unit and property-based tests in `tests/unit/presentation/test_plugin_manifest.py`
  - [x] 3.1 Write concrete unit tests
    - Copy `PLUGIN_MANIFEST_SCHEMA` constant into the test file (avoid cross-service import from `ugsys-admin-panel`)
    - Use `httpx.AsyncClient` with `ASGITransport(app=app)` — same pattern as existing presentation tests; import `app` from `src.main`
    - Test: `GET /plugin-manifest.json` without `Authorization` header → HTTP 200
    - Test: response `Content-Type` is `application/json`
    - Test: response body passes `PLUGIN_MANIFEST_SCHEMA` via `jsonschema.validate`
    - Test: response body contains all required top-level fields: `name`, `version`, `entryPoint`, `routes`, `navigation`
    - Test: `name == "user-profile-service"` and `healthEndpoint == "/health"`
    - Test: no `requiredRoles` array in the manifest contains `"moderator"`
    - Test: route entry exists for `/users` with `label="Users"` and `requiredRoles` containing `"admin"`
    - Test: navigation entry exists with `label="Users"`, `icon="👤"`, `path="/users"`, `group="Users"`, `order=1`
    - Test: no route or navigation entry has `path == "/projects"` (scope boundary assertion)
    - Confirm `jsonschema` is in `pyproject.toml` before implementing
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

  - [ ]* 3.2 Write property-based test — Property 1: Schema conformance
    - **Property 1: Schema conformance** — `st.just(manifest)`, assert `jsonschema.validate(manifest, PLUGIN_MANIFEST_SCHEMA)` raises no exception
    - `@settings(max_examples=100)`
    - **Feature: ups-plugin-manifest, Property 1: For any invocation of GET /plugin-manifest.json, the parsed response body must pass the PLUGIN_MANIFEST_SCHEMA validator without errors**
    - **Validates: Requirements 1.4, 5.1**

  - [ ]* 3.3 Write property-based test — Property 2: JSON round-trip
    - **Property 2: JSON round-trip** — `st.just(manifest)`, assert `json.loads(json.dumps(manifest)) == manifest`
    - `@settings(max_examples=100)`
    - **Feature: ups-plugin-manifest, Property 2: For any invocation of GET /plugin-manifest.json, serialising the parsed response body to JSON and parsing it back must produce a document equal to the original**
    - **Validates: Requirements 1.3, 5.2**

  - [ ]* 3.4 Write property-based test — Property 3: Path prefix invariant
    - **Property 3: Path prefix invariant** — `st.sampled_from(all_paths)` where `all_paths` is the flattened list of `path` values from `routes` and `navigation`; assert `path.startswith("/")`
    - `@settings(max_examples=100)`
    - **Feature: ups-plugin-manifest, Property 3: For any RouteDescriptor in routes and any NavigationEntry in navigation, the path field must satisfy path.startswith("/")**
    - **Validates: Requirements 3.2, 4.4, 5.3, 6.7**

  - [ ]* 3.5 Write property-based test — Property 4: Non-empty navigation fields
    - **Property 4: Non-empty navigation fields** — `st.sampled_from(navigation)` where `navigation` is the list from the manifest; assert `len(entry["label"]) > 0`, `len(entry["icon"]) > 0`, `len(entry["path"]) > 0`
    - `@settings(max_examples=100)`
    - **Feature: ups-plugin-manifest, Property 4: For any NavigationEntry in navigation, the label, icon, and path fields must each be non-empty strings**
    - **Validates: Requirements 4.2, 4.3, 4.4, 5.4, 6.10**

  - [ ]* 3.6 Write property-based test — Property 5: Valid roles
    - **Property 5: Valid roles** — `st.sampled_from(all_roles)` where `all_roles` is the flattened list of all role strings from `routes[*].requiredRoles` and `navigation[*].requiredRoles`; assert `role in {"super_admin", "admin", "moderator", "auditor", "member", "guest", "system"}`
    - `@settings(max_examples=100)`
    - **Feature: ups-plugin-manifest, Property 5: For any role string in any requiredRoles array within routes or navigation, the value must be a member of the valid Platform_Role set**
    - **Validates: Requirements 3.3, 4.5, 5.5, 6.8**

  - [ ]* 3.7 Write property-based test — Property 6: Admin-only invariant
    - **Property 6: Admin-only invariant** — `st.sampled_from(all_roles)` (same collection as Property 5); assert `role != "moderator"`
    - `@settings(max_examples=100)`
    - **Feature: ups-plugin-manifest, Property 6: For any role string in any requiredRoles array within the manifest, the value must not equal "moderator"**
    - **Validates: Requirements 3.5, 4.7, 5.6, 6.6**

- [x] 4. Final checkpoint — Ensure all tests pass
  - Run `uv run pytest tests/unit/presentation/test_plugin_manifest.py -v` and confirm all tests are green
  - Verify `grep -n "from src.domain\|from src.infrastructure" src/presentation/api/v1/plugin_manifest.py` returns empty (arch-guard compliance)
  - Ask the user if any questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP
- Properties 5 and 6 share the same `all_roles` collection (flattened list of all role strings from routes and navigation) but must remain separate tests for independent failure signals
- The `entryPoint` value (`index-DS4a0gmi.js`) must be updated whenever the `ugsys-user-profile-service` web frontend is rebuilt
- `hypothesis` is already in `pyproject.toml` as a dev dependency — no new dependencies needed
- Confirm `jsonschema` is in `pyproject.toml` before implementing task 3
