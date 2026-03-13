# Requirements Document

## Introduction

The `ugsys-user-profile-service` currently returns 404 on `GET /plugin-manifest.json`, causing the admin panel's BFF seed loader to mark the service as `DEGRADED` and leave the user management section of the sidebar empty. This feature adds a static `GET /plugin-manifest.json` endpoint to the presentation layer that returns a valid Plugin Manifest document, enabling the admin panel to register the service successfully and render user management navigation entries.

The endpoint is public (no auth required), lives entirely in the presentation layer, and returns a hardcoded JSON document that satisfies the admin panel's JSON Schema contract.

The manifest declares user management as owned by this service — specifically the `/users` path in the admin panel. This path is currently rendered by a built-in shell view (`admin-shell/src/presentation/components/views/UserManagement.tsx`); the manifest formalises ownership so the admin panel can register it through the plugin system. All routes and navigation entries require `admin` or `super_admin` role — `moderator` access is intentionally excluded from the admin panel.

## Glossary

- **Plugin_Manifest_Endpoint**: The `GET /plugin-manifest.json` HTTP endpoint exposed by `ugsys-user-profile-service` at the service root (no `/api/v1/` prefix).
- **Manifest**: The JSON document returned by the Plugin_Manifest_Endpoint, conforming to the admin panel's Plugin Manifest JSON Schema.
- **BFF**: The Backend-for-Frontend component of `ugsys-admin-panel` that fetches manifests from registered services during seed loading.
- **Seed_Loader**: The startup process in `ugsys-admin-panel` that reads `seed_services.json` and fetches each service's manifest via its `manifest_url`.
- **Navigation_Entry**: A sidebar item contributed by the Manifest, with required fields `label`, `icon`, `path`, and `requiredRoles`.
- **Route_Descriptor**: A route entry contributed by the Manifest, with required fields `path`, `requiredRoles`, and `label`.
- **Platform_Role**: A valid role string from the platform role set: `super_admin`, `admin`, `moderator`, `auditor`, `member`, `guest`, `system`.
- **Admin_Panel_Schema**: The JSON Schema defined in `ugsys-admin-panel/src/application/interfaces/manifest_validator.py` that all manifests must pass.
- **AuthMiddleware**: The `ugsys-auth-client` middleware applied globally in `src/main.py` that attaches `request.state.user` when a valid Bearer token is present but does NOT block unauthenticated requests.
- **Icon_String**: A plain string rendered as raw text inside a `<span aria-hidden="true">` element in the admin panel's Sidebar component. No icon library is used — the value is displayed literally (emoji or unicode symbols are appropriate).
- **EntryPoint**: The URL of the JavaScript bundle that the admin shell loads as a micro-frontend module. For user-profile-service, this is the Vite-built JS bundle served from `https://profiles.apps.cloud.org.bo`. The asset filename includes a content hash that changes on every build; the manifest must reference the current build's filename.
- **Scope_Boundary**: User management (viewing/editing user profiles, preferences, avatars) is owned by `ugsys-user-profile-service`. Projects, subscriptions, and form schemas are out of scope for this manifest; they are declared by `ugsys-projects-registry` in its own manifest.

## Requirements

### Requirement 1: Plugin Manifest Endpoint

**User Story:** As the admin panel BFF, I want to fetch a plugin manifest from `ugsys-user-profile-service`, so that I can register the service, populate the user management sidebar section, and mark it as healthy instead of DEGRADED.

#### Acceptance Criteria

1. THE `Plugin_Manifest_Endpoint` SHALL respond to `GET /plugin-manifest.json` with HTTP status 200.
2. THE `Plugin_Manifest_Endpoint` SHALL return a response with `Content-Type: application/json`.
3. THE `Plugin_Manifest_Endpoint` SHALL return a response body that is valid JSON.
4. THE `Plugin_Manifest_Endpoint` SHALL return a response body that passes the `Admin_Panel_Schema` validator without errors.
5. THE `Plugin_Manifest_Endpoint` SHALL be accessible without an `Authorization` header (no authentication required).
6. WHEN the `AuthMiddleware` processes a request to `/plugin-manifest.json`, THE `AuthMiddleware` SHALL allow the request to proceed without requiring a JWT token.
7. THE `Plugin_Manifest_Endpoint` SHALL be registered in `src/main.py` at the service root, without the `/api/v1/` prefix.
8. THE `Plugin_Manifest_Endpoint` SHALL be implemented in `src/presentation/api/v1/plugin_manifest.py` with no imports from `src.domain` or `src.infrastructure`.

---

### Requirement 2: Manifest Content — Required Fields

**User Story:** As the admin panel BFF, I want the manifest to contain all required fields with correct values, so that the schema validator accepts it and the service is registered successfully.

#### Acceptance Criteria

1. THE `Manifest` SHALL contain a `name` field with the string value `"user-profile-service"`.
2. THE `Manifest` SHALL contain a `version` field whose value matches the pattern `^\d+\.\d+\.\d+$` (semver).
3. THE `Manifest` SHALL contain an `entryPoint` field with a valid URI pointing to the Vite-built JS bundle served from `https://profiles.apps.cloud.org.bo/assets/`. The exact filename (including content hash) SHALL match the current build artifact in `web/dist/assets/index-*.js`. At the time of writing, the current build artifact is `index-DS4a0gmi.js`, making the value `"https://profiles.apps.cloud.org.bo/assets/index-DS4a0gmi.js"`. This value MUST be updated whenever the web frontend is rebuilt.
4. THE `Manifest` SHALL contain a `healthEndpoint` field with the value `"/health"`.
5. THE `Manifest` SHALL contain a non-empty `routes` array.
6. THE `Manifest` SHALL contain a non-empty `navigation` array.

---

### Requirement 3: Manifest Content — Routes

**User Story:** As the admin panel BFF, I want the manifest to declare the admin routes owned by user-profile-service, so that the admin panel can register them for role-based access control.

#### Acceptance Criteria

1. THE `Manifest` SHALL include a `Route_Descriptor` with `path` `"/users"`, `label` `"Users"`, and `requiredRoles` containing `"admin"`.
2. FOR ALL `Route_Descriptor` entries in the `Manifest`, the `path` field SHALL start with `"/"`.
3. FOR ALL `Route_Descriptor` entries in the `Manifest`, every value in `requiredRoles` SHALL be a valid `Platform_Role` string.
4. FOR ALL `Route_Descriptor` entries in the `Manifest`, the `label` field SHALL be a non-empty string.
5. NO `Route_Descriptor` entry SHALL include `"moderator"` in `requiredRoles` — all admin panel routes require at minimum `"admin"` role.
6. THE `Manifest` SHALL NOT include a `Route_Descriptor` with `path` `"/projects"` — project management is owned by `ugsys-projects-registry`.

---

### Requirement 4: Manifest Content — Navigation

**User Story:** As the admin panel BFF, I want the manifest to declare sidebar navigation entries for user management, so that the admin panel can render them for users with sufficient roles.

#### Acceptance Criteria

1. THE `Manifest` SHALL include a `Navigation_Entry` with `label` `"Users"`, `icon` `"👤"`, `path` `"/users"`, `group` `"Users"`, `order` `1`, and `requiredRoles` containing `"admin"`.
2. FOR ALL `Navigation_Entry` items in the `Manifest`, the `label` field SHALL be a non-empty string.
3. FOR ALL `Navigation_Entry` items in the `Manifest`, the `icon` field SHALL be a non-empty `Icon_String` (emoji or unicode symbol rendered as raw text by the Sidebar component).
4. FOR ALL `Navigation_Entry` items in the `Manifest`, the `path` field SHALL be a non-empty string starting with `"/"`.
5. FOR ALL `Navigation_Entry` items in the `Manifest`, every value in `requiredRoles` SHALL be a valid `Platform_Role` string.
6. FOR ALL `Navigation_Entry` items in the `Manifest`, the `group` field, when present, SHALL be a non-empty string.
7. NO `Navigation_Entry` SHALL include `"moderator"` in `requiredRoles` — all sidebar entries require at minimum `"admin"` role.
8. THE `Manifest` SHALL NOT include a `Navigation_Entry` with `path` `"/projects"` — project navigation is owned by `ugsys-projects-registry`.

---

### Requirement 5: Manifest Correctness Properties (PBT)

**User Story:** As a developer, I want property-based tests to verify the manifest's structural invariants, so that any future change to the manifest content is caught before it breaks the admin panel integration.

#### Acceptance Criteria

1. FOR ALL invocations of `GET /plugin-manifest.json`, the response body SHALL pass the `Admin_Panel_Schema` validator (schema-conformance invariant).
2. FOR ALL invocations of `GET /plugin-manifest.json`, serializing the response body to JSON and parsing it back SHALL produce a document equal to the original (JSON round-trip property).
3. FOR ALL `Route_Descriptor` entries in the `Manifest`, the `path` value SHALL satisfy `path.startswith("/")` (path prefix invariant).
4. FOR ALL `Navigation_Entry` items in the `Manifest`, the `label`, `icon`, and `path` fields SHALL each be non-empty strings (non-empty fields invariant).
5. FOR ALL role strings in any `requiredRoles` array within the `Manifest`, the value SHALL be a member of the set `{"super_admin", "admin", "moderator", "auditor", "member", "guest", "system"}` (valid role invariant).
6. NO role string in any `requiredRoles` array within the `Manifest` SHALL equal `"moderator"` — all entries require at minimum `"admin"` (admin-only invariant).

---

### Requirement 6: Unit Tests

**User Story:** As a developer, I want unit tests for the plugin manifest endpoint in `tests/unit/presentation/`, so that regressions are caught in CI before deployment.

#### Acceptance Criteria

1. THE test suite SHALL include a test that verifies `GET /plugin-manifest.json` returns HTTP 200 without an `Authorization` header.
2. THE test suite SHALL include a test that verifies the response `Content-Type` is `application/json`.
3. THE test suite SHALL include a test that verifies the response body passes the `Admin_Panel_Schema` validator.
4. THE test suite SHALL include a test that verifies the response body contains all required fields: `name`, `version`, `entryPoint`, `routes`, and `navigation`.
5. THE test suite SHALL include a test that verifies `name` equals `"user-profile-service"` and `healthEndpoint` equals `"/health"`.
6. THE test suite SHALL include a test that verifies no `requiredRoles` array in the manifest contains `"moderator"`.
7. THE test suite SHALL include a property-based test that verifies all `path` values in `routes` start with `"/"`.
8. THE test suite SHALL include a property-based test that verifies all `requiredRoles` values across `routes` and `navigation` are valid `Platform_Role` strings.
9. THE test suite SHALL include a property-based test that verifies the JSON round-trip property: `json.loads(json.dumps(manifest)) == manifest`.
10. THE test suite SHALL include a property-based test that verifies all `Navigation_Entry` fields `label`, `icon`, and `path` are non-empty strings.
