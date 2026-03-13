# Design Document — ups-plugin-manifest

## Overview

This feature adds a `GET /plugin-manifest.json` endpoint to `ugsys-user-profile-service` so the
`ugsys-admin-panel` BFF seed loader can fetch it, register the service as `ACTIVE`, and populate
the user management section of the sidebar navigation.

The endpoint is entirely static — it returns a hardcoded JSON document with no database access,
no authentication, and no application or domain layer involvement. It lives exclusively in the
presentation layer, following the same pattern as `health.py`.

No change to `ugsys-admin-panel/config/seed_services.json` is required: the `projects-registry`
entry already has `min_role: "admin"` and `manifest_url: "https://profiles.apps.cloud.org.bo/plugin-manifest.json"`.

### Key design decisions

- **Static JSON, no service injection**: The manifest content is fixed at deploy time. There is no
  reason to involve the application or domain layers. The router returns a plain `dict` literal,
  identical to how `health.py` works.
- **No new dependencies**: `hypothesis` is already in `pyproject.toml` as a dev dependency.
  `jsonschema` is already available via `ugsys-admin-panel`'s shared validator; for tests in
  `ugsys-user-profile-service` we copy the schema constant directly into the test file to avoid a
  cross-service import.
- **No AuthMiddleware blocking**: Inspecting `src/main.py` confirms there is no `AuthMiddleware`
  in the middleware stack — JWT token service is wired via `dependency_overrides` into the
  `profiles` router only. The `plugin_manifest` router therefore requires no auth configuration
  at all; it is public by default.
- **No `/api/v1/` prefix**: The admin panel's `seed_services.json` hardcodes
  `manifest_url: "https://profiles.apps.cloud.org.bo/plugin-manifest.json"` — the router must be
  registered at the service root, matching the pattern of `health.py`.

---

## Architecture

The change touches exactly two files in `ugsys-user-profile-service`:

```
ugsys-user-profile-service/
└── src/
    └── presentation/
        └── api/
            └── v1/
                └── plugin_manifest.py   ← NEW router (presentation layer only)
    └── main.py                          ← register new router (no prefix)

tests/unit/presentation/
└── test_plugin_manifest.py              ← NEW unit + PBT tests
```

### Layer boundary compliance

The `plugin_manifest.py` router:
- imports only from `fastapi` and Python stdlib
- has **zero** imports from `src.domain`, `src.application`, or `src.infrastructure`
- passes the arch-guard CI grep check by construction

```
presentation  →  (nothing — static response)
```

### Request flow

```
BFF Seed Loader
    │  GET /plugin-manifest.json
    ▼
API Gateway → Lambda
    │
    ▼
FastAPI middleware stack
  CorrelationIdMiddleware   (attaches X-Request-ID)
  SecurityHeadersMiddleware (stamps security headers)
  RateLimitMiddleware       (token bucket, 60 req/min — falls back to IP for unauthenticated)
    │
    ▼
plugin_manifest.router
  GET /plugin-manifest.json
    │
    ▼
Returns hardcoded dict → FastAPI serialises to JSON
```

Note: there is no `AuthMiddleware` in the middleware stack for this service. JWT validation is
injected only into the `profiles` router via `dependency_overrides`. The manifest endpoint is
therefore public without any additional configuration.

---

## Components and Interfaces

### `src/presentation/api/v1/plugin_manifest.py`

A single-file router with one endpoint. No dependencies injected.

```python
router = APIRouter(tags=["Plugin Manifest"])

@router.get("/plugin-manifest.json")
async def get_plugin_manifest() -> dict[str, object]:
    return { ... }  # hardcoded manifest dict
```

The return type is `dict[str, object]` — FastAPI serialises it to JSON with
`Content-Type: application/json` automatically.

### `src/main.py` — router registration

```python
from src.presentation.api.v1 import plugin_manifest

# inside create_app(), after existing routers:
app.include_router(plugin_manifest.router)   # no prefix — service root
```

This mirrors the existing `app.include_router(health.router)` line.

---

## Data Models

The manifest is a plain Python `dict` that conforms to the `PLUGIN_MANIFEST_SCHEMA` defined in
`ugsys-admin-panel/src/application/interfaces/manifest_validator.py`.

### Schema summary (from `manifest_validator.py`)

| Field | Type | Required | Constraint |
|---|---|---|---|
| `name` | string | ✅ | minLength: 1 |
| `version` | string | ✅ | pattern: `^\d+\.\d+\.\d+$` |
| `entryPoint` | string | ✅ | format: uri |
| `routes` | array | ✅ | items: RouteDescriptor |
| `navigation` | array | ✅ | items: NavigationEntry |
| `healthEndpoint` | string | ❌ | — |
| `stylesheetUrl` | string | ❌ | format: uri |
| `configSchema` | object | ❌ | — |
| `requiredPermissions` | array | ❌ | items: string |

**RouteDescriptor** (required: `path`, `requiredRoles`, `label`)

**NavigationEntry** (required: `label`, `icon`, `path`, `requiredRoles`; optional: `group`, `order`)

### Manifest content

```json
{
  "name": "user-profile-service",
  "version": "0.1.0",
  "entryPoint": "https://profiles.apps.cloud.org.bo/assets/index-DS4a0gmi.js",
  "healthEndpoint": "/health",
  "routes": [
    {"path": "/users", "label": "Users", "requiredRoles": ["admin", "super_admin"]}
  ],
  "navigation": [
    {"label": "Users", "icon": "👤", "path": "/users", "group": "Users", "order": 1, "requiredRoles": ["admin", "super_admin"]}
  ]
}
```

> **Maintenance note**: `entryPoint` contains a content-hash filename (`index-DS4a0gmi.js`).
> This value must be updated whenever the `ugsys-user-profile-service` web frontend is rebuilt.
> The current value matches the build artifact in `web/dist/assets/` at the time of writing.

---

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a
system — essentially, a formal statement about what the system should do. Properties serve as the
bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Schema conformance

*For any* invocation of `GET /plugin-manifest.json`, the parsed response body must pass the
`PLUGIN_MANIFEST_SCHEMA` JSON Schema validator without errors.

**Validates: Requirements 1.4, 5.1**

---

### Property 2: JSON round-trip

*For any* invocation of `GET /plugin-manifest.json`, serialising the parsed response body to JSON
and parsing it back must produce a document equal to the original:
`json.loads(json.dumps(manifest)) == manifest`.

**Validates: Requirements 1.3, 5.2**

---

### Property 3: Path prefix invariant

*For any* `RouteDescriptor` in `routes` and any `NavigationEntry` in `navigation`, the `path`
field must satisfy `path.startswith("/")`.

**Validates: Requirements 3.2, 4.4, 5.3**

---

### Property 4: Non-empty navigation fields

*For any* `NavigationEntry` in `navigation`, the `label`, `icon`, and `path` fields must each be
non-empty strings (i.e. `len(field) > 0`).

**Validates: Requirements 4.2, 4.3, 4.4, 5.4**

---

### Property 5: Valid roles

*For any* role string in any `requiredRoles` array within `routes` or `navigation`, the value must
be a member of the valid Platform_Role set:
`{"super_admin", "admin", "moderator", "auditor", "member", "guest", "system"}`.

**Validates: Requirements 3.3, 4.5, 5.5**

---

### Property 6: Admin-only invariant

*For any* role string in any `requiredRoles` array within the manifest, the value must not equal
`"moderator"`. All entries require at minimum `"admin"` role.

**Validates: Requirements 3.5, 4.7, 5.6**

---

## Error Handling

The endpoint has no failure modes under normal operation — it returns a hardcoded dict with no I/O.

| Scenario | Behaviour |
|---|---|
| Request without `Authorization` header | 200 OK — no AuthMiddleware in stack |
| Request with invalid `Authorization` header | 200 OK — no AuthMiddleware in stack |
| Request with valid `Authorization` header | 200 OK — same response regardless |
| Lambda cold start | No impact — no I/O in the endpoint |

The only realistic error path is a 500 from an unhandled exception in the middleware stack, which
is already handled by `unhandled_exception_handler` registered in `main.py`.

---

## Testing Strategy

### Dual testing approach

Both unit tests and property-based tests are required. They are complementary:
- Unit tests verify specific examples and concrete values
- Property tests verify universal invariants across all inputs

Since the manifest is static, "all inputs" means all invocations of the endpoint — the properties
verify that the hardcoded content satisfies its structural invariants, and that no future edit
accidentally breaks them.

### Unit tests (`tests/unit/presentation/test_plugin_manifest.py`)

Use `httpx.AsyncClient` with `ASGITransport(app=app)` — the same pattern as existing presentation
tests in this service. No mocking needed.

Concrete example tests:
1. `GET /plugin-manifest.json` without `Authorization` → HTTP 200
2. Response `Content-Type` is `application/json`
3. Response body passes `PLUGIN_MANIFEST_SCHEMA` validator
4. Response body contains all required fields: `name`, `version`, `entryPoint`, `routes`, `navigation`
5. `name == "user-profile-service"` and `healthEndpoint == "/health"`
6. No `requiredRoles` array in the manifest contains `"moderator"`
7. Specific route entry exists for `/users` with label `"Users"` and `requiredRoles` containing `"admin"`
8. Specific navigation entry exists with `label="Users"`, `icon="👤"`, `path="/users"`, `group="Users"`, `order=1`
9. No route or navigation entry has `path == "/projects"` (scope boundary assertion)

### Property-based tests (Hypothesis)

Library: `hypothesis` (already in `pyproject.toml` as a dev dependency).

Since the manifest is static, the PBT strategy is to fetch the manifest once and then run
assertions over its sub-collections (routes list, navigation list, all role arrays). Hypothesis
`@given` is used with `st.just(manifest)` or by parameterising over the list elements using
`st.sampled_from`.

Each property test runs a minimum of 100 examples (`@settings(max_examples=100)`).

Tag format in test comments: `Feature: ups-plugin-manifest, Property {N}: {property_text}`

| Property | Test name | Strategy |
|---|---|---|
| P1: Schema conformance | `test_manifest_passes_schema` | `st.just(manifest)` |
| P2: JSON round-trip | `test_manifest_json_round_trip` | `st.just(manifest)` |
| P3: Path prefix | `test_all_paths_start_with_slash` | `st.sampled_from(all_paths)` |
| P4: Non-empty nav fields | `test_navigation_fields_non_empty` | `st.sampled_from(navigation)` |
| P5: Valid roles | `test_all_roles_are_valid_platform_roles` | `st.sampled_from(all_roles)` |
| P6: Admin-only | `test_no_moderator_in_required_roles` | `st.sampled_from(all_roles)` |

> Properties 5 and 6 both operate over the same `all_roles` collection (flattened list of all role
> strings from routes and navigation). They can share a fixture but must remain separate tests to
> preserve independent failure signals.

### Architecture guard

The CI `arch-guard` job already runs:
```bash
grep -rn "from src.infrastructure\|from src.presentation\|from src.application" src/domain/
grep -rn "from src.infrastructure\|from src.presentation" src/application/
```

An additional check should verify `plugin_manifest.py` has no domain/infra imports:
```bash
grep -n "from src.domain\|from src.infrastructure" src/presentation/api/v1/plugin_manifest.py
# must return empty
```
