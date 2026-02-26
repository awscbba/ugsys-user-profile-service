# User Profile Hardening — Bugfix Tasks

## Phase 1: Exploratory Fault Condition Checking

> These tests run on **unfixed** code and are expected to **fail**. They confirm the bug exists and validate root cause analysis.

### Gap 1 — Security Headers (Exploratory)

- [x] 1.1 Write exploratory tests for security header defects in `tests/unit/presentation/test_security_headers.py`
  - [x] 1.1.1 Assert `X-XSS-Protection: 0` on any response (will fail — current value is `1; mode=block`)
  - [x] 1.1.2 Assert `Strict-Transport-Security` contains `preload` (will fail — missing directive)
  - [x] 1.1.3 Assert `Content-Security-Policy: default-src 'none'; frame-ancestors 'none'` (will fail — current is `default-src 'self'`)
  - [x] 1.1.4 Assert `Permissions-Policy` header present on any response (will fail — missing)
  - [x] 1.1.5 Assert `Cross-Origin-Opener-Policy` header present on any response (will fail — missing)
  - [x] 1.1.6 Assert `Cross-Origin-Resource-Policy` header present on any response (will fail — missing)
  - [x] 1.1.7 Assert `server` header absent from any response (will fail — currently exposed)
  - [x] 1.1.8 Assert `Cache-Control: no-store, no-cache, must-revalidate` present on `/api/*` path responses (will fail — missing)
  - [x] 1.1.9 Assert middleware uses `_SECURITY_HEADERS` private attribute (will fail — currently public `SECURITY_HEADERS`)
- [x] 1.2 [PBT] Write property test: for any HTTP path, `Cache-Control` is present iff path starts with `/api/` — run on unfixed code to observe failure in `tests/unit/presentation/test_security_headers.py`

### Gap 2 — DynamoDB ClientError Wrapping (Exploratory)

- [x] 1.3 Write exploratory tests for ClientError leaks in `tests/unit/infrastructure/test_dynamodb_profile_repository.py`
  - [x] 1.3.1 Mock `put_item` to raise `ClientError` — assert `RepositoryError` raised (will fail — raw `ClientError` propagates)
  - [x] 1.3.2 Mock `get_item` to raise `ClientError` — assert `RepositoryError` raised (will fail)
  - [x] 1.3.3 Mock `scan` to raise `ClientError` — assert `RepositoryError` raised (will fail)
  - [x] 1.3.4 Mock `delete_item` to raise `ClientError` — assert `RepositoryError` raised (will fail)
  - [x] 1.3.5 Mock `put_item` to raise `ConditionalCheckFailedException` in `save()` — assert `RepositoryError` with `error_code="REPOSITORY_ERROR"` (will fail)
  - [x] 1.3.6 Mock `put_item` to raise `ConditionalCheckFailedException` in `update()` — assert `NotFoundError` with `user_message="Profile not found"` (will fail)
- [x] 1.4 [PBT] Write property test: for any `ClientError` code raised by any DynamoDB operation, the repository raises `RepositoryError` (or `NotFoundError` for `ConditionalCheckFailedException` on `update()`) — run on unfixed code to observe failure

### Gap 3 — Async I/O DynamoDB (Exploratory)

- [x] 1.5 Write exploratory test asserting no synchronous `boto3.resource("dynamodb")` calls exist in async methods of `DynamoDBProfileRepository` (will fail — currently uses sync boto3)

### Gap 4 — Rate Limiting (Exploratory)

- [x] 1.6 Write exploratory tests for rate limiting defects in `tests/unit/presentation/test_rate_limiting.py`
  - [x] 1.6.1 Send two requests with same JWT `sub` from different IPs — assert shared counter (will fail — currently IP-keyed)
  - [x] 1.6.2 Send 11 requests in 1 second — assert 429 returned (will fail — burst window not enforced)
  - [x] 1.6.3 Send 1001 requests in 1 hour — assert 429 returned (will fail — hour window not enforced)
  - [x] 1.6.4 Assert `X-RateLimit-Limit` present on 200 response (will fail — header missing)
  - [x] 1.6.5 Assert `X-RateLimit-Remaining` present on 200 response (will fail — header missing)
  - [x] 1.6.6 Assert `X-RateLimit-Reset` present on 200 response (will fail — header missing)
  - [x] 1.6.7 Exceed rate limit — assert `Retry-After` present on 429 response (will fail — header missing)
- [x] 1.7 [PBT] Write property test: for any two distinct JWT `sub` values, rate limit counters are independent — run on unfixed code to observe failure

### Gap 5 — Exception Handler (Exploratory)

- [x] 1.8 Write exploratory tests for exception handler defects in `tests/unit/presentation/test_exception_handler.py`
  - [x] 1.8.1 Raise `AccountLockedError` — assert HTTP 423 returned (will fail — currently falls through to 500)
  - [x] 1.8.2 Set `correlation_id_var`, raise domain exception — assert `request_id` in error log equals `correlation_id_var.get()` (will fail — currently reads from request header)
- [x] 1.9 [PBT] Write property test: for any domain exception type in the hierarchy, the handler returns the correct HTTP status code — run on unfixed code to observe `AccountLockedError` failure

### Gap 6 — Async I/O S3 (Exploratory)

- [x] 1.10 Write exploratory test asserting no synchronous `boto3.client("s3")` calls exist in async methods of `S3AvatarStorage` (will fail — currently uses sync boto3)

---

## Phase 2: Fix Implementation

> Implement fixes in the order specified. Gap 2 MUST be applied before Gap 3 — both target the same file.

### Gap 1 — Security Headers

- [x] 2.1 Fix `src/presentation/middleware/security_headers.py`
  - [x] 2.1.1 Rename public `SECURITY_HEADERS` dict to `_SECURITY_HEADERS`
  - [x] 2.1.2 Set `X-XSS-Protection: 0`
  - [x] 2.1.3 Set `Strict-Transport-Security: max-age=31536000; includeSubDomains; preload`
  - [x] 2.1.4 Set `Content-Security-Policy: default-src 'none'; frame-ancestors 'none'`
  - [x] 2.1.5 Add `Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=()`
  - [x] 2.1.6 Add `Cross-Origin-Opener-Policy: same-origin`
  - [x] 2.1.7 Add `Cross-Origin-Resource-Policy: same-origin`
  - [x] 2.1.8 In `dispatch()`, call `response.headers.pop("server", None)` after setting headers
  - [x] 2.1.9 In `dispatch()`, add conditional: if `request.url.path.startswith("/api/")`, set `Cache-Control: no-store, no-cache, must-revalidate`

### Gap 2 — DynamoDB ClientError Wrapping (apply BEFORE Gap 3)

- [x] 2.2 Fix `src/infrastructure/persistence/dynamodb_profile_repository.py` — ClientError wrapping
  - [x] 2.2.1 Add `from botocore.exceptions import ClientError` import
  - [x] 2.2.2 Add `_raise_repository_error(self, operation: str, e: ClientError) -> None` method — log full error via structlog, raise `RepositoryError(user_message="An unexpected error occurred")`
  - [x] 2.2.3 Wrap `put_item` call in `try/except ClientError`
  - [x] 2.2.4 Wrap `get_item` call in `try/except ClientError`
  - [x] 2.2.5 Wrap `scan` call in `try/except ClientError`
  - [x] 2.2.6 Wrap `delete_item` call in `try/except ClientError`
  - [x] 2.2.7 In `save()`: catch `ConditionalCheckFailedException` → raise `RepositoryError(error_code="REPOSITORY_ERROR", user_message="An unexpected error occurred")`
  - [x] 2.2.8 In `update()`: catch `ConditionalCheckFailedException` → raise `NotFoundError(error_code="NOT_FOUND", user_message="Profile not found")`

### Gap 3 — Async I/O DynamoDB (apply AFTER Gap 2)

- [x] 2.3 Migrate `src/infrastructure/persistence/dynamodb_profile_repository.py` to aioboto3
  - [x] 2.3.1 Verify `aioboto3` is in `pyproject.toml` dependencies — add if missing
  - [x] 2.3.2 Replace `boto3.resource("dynamodb", ...)` with `self._session = aioboto3.Session()` in `__init__`
  - [x] 2.3.3 Update `__init__` signature to `(self, table_name: str, region: str, session: aioboto3.Session) -> None`
  - [x] 2.3.4 Replace each sync DynamoDB call with `async with self._session.client("dynamodb", region_name=self._region) as client:` context manager
  - [x] 2.3.5 Update `src/main.py` to pass `session=aioboto3.Session()` when constructing `DynamoDBProfileRepository`

### Gap 4 — Rate Limiting

- [x] 2.4 Fix `src/presentation/middleware/rate_limiting.py`
  - [x] 2.4.1 Replace any module-level counter dict with `self._counters: dict[str, list[float]] = defaultdict(list)` in `__init__`
  - [x] 2.4.2 Add `_extract_key(self, request: Request) -> str` — decode Bearer JWT (no sig verification), extract `sub` → `f"user:{sub}"`; fallback to `X-Forwarded-For` / `client.host` → `f"ip:{ip}"`
  - [x] 2.4.3 Add window constants: `_WINDOW_MINUTE=60.0`, `_WINDOW_HOUR=3600.0`, `_BURST_WINDOW=1.0`
  - [x] 2.4.4 Add limit constants: `_MAX_PER_MINUTE=60`, `_MAX_PER_HOUR=1000`, `_MAX_BURST=10`
  - [x] 2.4.5 In `dispatch()`: prune `self._counters[key]` to 1-hour window; compute burst/minute/hour counts; return 429 with `Retry-After` if any limit exceeded
  - [x] 2.4.6 On non-429 responses: set `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset` headers

### Gap 5 — Exception Handler

- [x] 2.5 Fix `src/presentation/middleware/exception_handler.py`
  - [x] 2.5.1 Add `AccountLockedError: 423` to `_STATUS_MAP`
  - [x] 2.5.2 Import `correlation_id_var` from `src/presentation/middleware/correlation_id.py`
  - [x] 2.5.3 Replace `request.headers.get("X-Request-ID", "")` with `correlation_id_var.get("")`

### Gap 6 — Async I/O S3

- [x] 2.6 Migrate `src/infrastructure/adapters/s3_avatar_storage.py` to aioboto3
  - [x] 2.6.1 Verify `aioboto3` is in `pyproject.toml` dependencies (already confirmed in 2.3.1)
  - [x] 2.6.2 Replace `boto3.client("s3", ...)` with `self._session = aioboto3.Session()` in `__init__`
  - [x] 2.6.3 Update `__init__` signature to `(self, bucket_name: str, region: str, session: aioboto3.Session) -> None`
  - [x] 2.6.4 Replace each sync S3 call with `async with self._session.client("s3", region_name=self._region) as client:` context manager
  - [x] 2.6.5 Update `src/main.py` to pass `session=aioboto3.Session()` when constructing `S3AvatarStorage`

---

## Phase 3: Fix Checking

> These tests run on **fixed** code and are expected to **pass**. They verify the fix works for all buggy inputs.

### Gap 1 — Security Headers (Fix Checking)

- [x] 3.1 Extend `tests/unit/presentation/test_security_headers.py` with fix-checking assertions
  - [x] 3.1.1 Assert all 9 required headers present with exact platform-contract values
  - [x] 3.1.2 Assert `server` header absent from responses
  - [x] 3.1.3 Assert `Cache-Control` present on `/api/*` paths and absent on non-`/api/` paths
  - [x] 3.1.4 Assert middleware attribute is `_SECURITY_HEADERS` (private)
- [x] 3.2 [PBT] Run the Cache-Control path property test (from 1.2) on fixed code — assert it passes

### Gap 2 — DynamoDB ClientError Wrapping (Fix Checking)

- [x] 3.3 Extend `tests/unit/infrastructure/test_dynamodb_profile_repository.py` with fix-checking assertions
  - [x] 3.3.1 Mock each DynamoDB operation to raise `ClientError` — assert `RepositoryError` raised with safe `user_message`
  - [x] 3.3.2 Mock `ConditionalCheckFailedException` in `save()` — assert `RepositoryError(error_code="REPOSITORY_ERROR")`
  - [x] 3.3.3 Mock `ConditionalCheckFailedException` in `update()` — assert `NotFoundError(error_code="NOT_FOUND", user_message="Profile not found")`
- [x] 3.4 [PBT] Run the ClientError code property test (from 1.4) on fixed code — assert it passes

### Gap 3 — Async I/O DynamoDB (Fix Checking)

- [x] 3.5 Extend `tests/unit/infrastructure/test_dynamodb_profile_repository.py`
  - [x] 3.5.1 Assert `DynamoDBProfileRepository` uses `aioboto3` async context manager in all async methods
  - [x] 3.5.2 Assert no synchronous `boto3.resource()` calls remain

### Gap 4 — Rate Limiting (Fix Checking)

- [-] 3.6 Extend `tests/unit/presentation/test_rate_limiting.py` with fix-checking assertions
  - [x] 3.6.1 Assert two requests with same JWT `sub` from different IPs share a counter
  - [x] 3.6.2 Assert 11 requests in 1 second returns 429
  - [x] 3.6.3 Assert 1001 requests in 1 hour returns 429
  - [x] 3.6.4 Assert `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset` present on all non-429 responses
  - [x] 3.6.5 Assert `Retry-After` present on 429 responses
  - [x] 3.6.6 Assert unauthenticated requests fall back to IP-based keying
- [x] 3.7 [PBT] Run the sub isolation property test (from 1.7) on fixed code — assert it passes

### Gap 5 — Exception Handler (Fix Checking)

- [x] 3.8 Extend `tests/unit/presentation/test_exception_handler.py` with fix-checking assertions
  - [x] 3.8.1 Raise `AccountLockedError` — assert HTTP 423 returned
  - [x] 3.8.2 Set `correlation_id_var`, raise domain exception — assert `request_id` in error response equals `correlation_id_var.get()`
- [x] 3.9 [PBT] Run the exception type → status code property test (from 1.9) on fixed code — assert it passes for all types including `AccountLockedError`

### Gap 6 — Async I/O S3 (Fix Checking)

- [x] 3.10 Extend `tests/unit/infrastructure/test_s3_avatar_storage.py`
  - [x] 3.10.1 Assert `S3AvatarStorage` uses `aioboto3` async context manager in all async methods
  - [x] 3.10.2 Assert no synchronous `boto3.client("s3")` calls remain

---

## Phase 4: Preservation Checking

> These tests run on **fixed** code and are expected to **pass**. They verify existing behavior is unchanged.

### Preservation — Security Headers

- [x] 4.1 Assert `X-Content-Type-Options: nosniff` unchanged after security headers fix
- [x] 4.2 Assert `X-Frame-Options: DENY` unchanged after security headers fix
- [x] 4.3 Assert `Referrer-Policy: strict-origin-when-cross-origin` unchanged after security headers fix

### Preservation — DynamoDB Operations

- [x] 4.4 [PBT] Write property test: for any valid profile payload, `_to_item`/`_from_item` round-trip returns the same domain entity after aioboto3 migration — assert passes in `tests/unit/infrastructure/test_dynamodb_profile_repository.py`
- [x] 4.5 Write integration tests in `tests/integration/test_dynamodb_profile_repository.py` (moto-based)
  - [x] 4.5.1 `save()` then `find_by_id()` round-trip returns correct domain entity
  - [x] 4.5.2 `update()` persists changes and returns updated entity
  - [x] 4.5.3 `delete()` removes item; subsequent `find_by_id()` returns `None`
  - [x] 4.5.4 `ConditionalCheckFailedException` on `save()` raises `RepositoryError`
  - [x] 4.5.5 `ConditionalCheckFailedException` on `update()` raises `NotFoundError`

### Preservation — S3 Avatar Storage

- [x] 4.6 Write integration tests in `tests/integration/test_s3_avatar_storage.py` (moto-based)
  - [x] 4.6.1 Upload avatar stores object in S3 and returns correct URL
  - [x] 4.6.2 Retrieve avatar returns correct presigned URL or object
  - [x] 4.6.3 Delete avatar removes object from S3

### Preservation — Profile CRUD Flow

- [x] 4.7 Write integration tests in `tests/integration/test_profile_flow.py`
  - [x] 4.7.1 `GET /api/v1/profiles/{id}` returns 200 with profile data (Requirement 3.1)
  - [x] 4.7.2 `POST /api/v1/profiles` returns 201 and persists profile (Requirement 3.2)
  - [x] 4.7.3 `PUT /api/v1/profiles/{id}` returns updated profile data (Requirement 3.3)
  - [x] 4.7.4 `DELETE /api/v1/profiles/{id}` returns 204 (Requirement 3.4)
  - [x] 4.7.5 `GET /api/v1/profiles/{id}` for missing profile returns 404 (Requirement 3.5)
  - [x] 4.7.6 Avatar upload stores in S3 and returns avatar URL (Requirement 3.6)
  - [x] 4.7.7 `GET /health` returns 200 without authentication (Requirement 3.7)
  - [x] 4.7.8 Requests exceeding 60 req/min return 429 (Requirement 3.8)

### Preservation — Exception Status Codes

- [x] 4.8 [PBT] Write property test: for any of `ValidationError`, `NotFoundError`, `ConflictError`, `AuthenticationError`, `AuthorizationError` — assert status codes 422, 404, 409, 401, 403 respectively are unchanged after exception handler fix in `tests/unit/presentation/test_exception_handler.py`
