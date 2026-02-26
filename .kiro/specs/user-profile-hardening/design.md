# User Profile Hardening — Bugfix Design

## Overview

The `ugsys-user-profile-service` service has six enterprise pattern compliance gaps that must be
resolved before production deployment. Each gap is a security or reliability defect relative to
the platform contract. The fix strategy is surgical: change only the code paths that are
non-compliant, leaving all profile CRUD flows, avatar handling, and passing tests untouched.

The six gaps and their target files are:

| Gap | Area | Files |
|-----|------|-------|
| 1 | Security headers | `src/presentation/middleware/security_headers.py` |
| 2 | DynamoDB ClientError wrapping | `src/infrastructure/persistence/dynamodb_profile_repository.py` |
| 3 | Async I/O — DynamoDB | `src/infrastructure/persistence/dynamodb_profile_repository.py` |
| 4 | Rate limiting (per-user, 3 windows, headers) | `src/presentation/middleware/rate_limiting.py` |
| 5 | Exception handler mapping | `src/presentation/middleware/exception_handler.py` |
| 6 | Async I/O — S3 | `src/infrastructure/adapters/s3_avatar_storage.py` |

---

## Glossary

- **Bug_Condition (C)**: Any of the 20 defect clauses (1.1–1.20) — the condition under which the
  service behaves incorrectly relative to the platform contract.
- **Property (P)**: The desired correct behavior for each bug condition (clauses 2.1–2.19).
- **Preservation**: All profile CRUD flows, avatar handling, and existing correct behaviors
  (clauses 3.1–3.11) that must remain unchanged after the fix.
- **isBugCondition(input)**: Pseudocode predicate that returns `true` when an input triggers one
  of the 20 defect clauses.
- **SecurityHeadersMiddleware**: The middleware in `src/presentation/middleware/security_headers.py`
  that injects security response headers.
- **RateLimitMiddleware**: The middleware in `src/presentation/middleware/rate_limiting.py` that
  enforces per-user/IP request rate limits.
- **DynamoDBProfileRepository**: The adapter in `src/infrastructure/persistence/dynamodb_profile_repository.py`
  implementing the `ProfileRepository` port.
- **S3AvatarStorage**: The adapter in `src/infrastructure/adapters/s3_avatar_storage.py`
  implementing the avatar storage port.
- **ClientError**: The `botocore.exceptions.ClientError` raised by boto3/aioboto3 on AWS API failures.
- **RepositoryError**: Domain exception (`src/domain/exceptions.py`) for infrastructure failures.
- **NotFoundError**: Domain exception for missing resources.
- **AccountLockedError**: Domain exception for locked accounts — must map to HTTP 423.
- **correlation_id_var**: The `ContextVar[str]` set by `CorrelationIdMiddleware` — the authoritative
  source of the request ID within a request lifecycle.

---

## Bug Details

### Fault Condition

The bugs manifest across six independent areas. Each area has its own `isBugCondition` predicate.


**Gap 1 — Security Headers Formal Specification:**
```
FUNCTION isBugCondition_SecurityHeaders(response)
  INPUT: response of type HTTP Response
  OUTPUT: boolean

  RETURN response.headers["X-XSS-Protection"] != "0"
      OR response.headers["Strict-Transport-Security"] does not contain "preload"
      OR response.headers["Content-Security-Policy"] != "default-src 'none'; frame-ancestors 'none'"
      OR "Permissions-Policy" NOT IN response.headers
      OR "Cross-Origin-Opener-Policy" NOT IN response.headers
      OR "Cross-Origin-Resource-Policy" NOT IN response.headers
      OR ("server" IN response.headers AND response.headers["server"] != "")
      OR (request.path STARTS_WITH "/api/" AND "Cache-Control" NOT IN response.headers)
      OR SECURITY_HEADERS dict is public (not underscore-prefixed as _SECURITY_HEADERS)
END FUNCTION
```

**Gap 2 — DynamoDB ClientError Wrapping Formal Specification:**
```
FUNCTION isBugCondition_ClientError(exception, caller_layer)
  INPUT: exception raised during DynamoDB operation, caller_layer = "application"
  OUTPUT: boolean

  RETURN exception IS ClientError
      AND caller_layer == "application"
      -- i.e., ClientError was not caught and re-raised as RepositoryError/NotFoundError
END FUNCTION
```

**Gap 3 — Async I/O DynamoDB Formal Specification:**
```
FUNCTION isBugCondition_AsyncIO_DynamoDB(repository_method)
  INPUT: repository_method = any async method in DynamoDBProfileRepository
  OUTPUT: boolean

  RETURN repository_method calls boto3.resource("dynamodb") synchronously
      -- i.e., uses synchronous I/O inside an async def, blocking the event loop
END FUNCTION
```

**Gap 4 — Rate Limiting Formal Specification:**
```
FUNCTION isBugCondition_RateLimit(request, response)
  INPUT: request of type HTTP Request, response of type HTTP Response
  OUTPUT: boolean

  has_jwt = request has valid Bearer token with "sub" claim
  keyed_by_sub = rate limit counter key includes JWT sub

  RETURN (has_jwt AND NOT keyed_by_sub)
      OR (response.status != 429 AND "X-RateLimit-Limit" NOT IN response.headers)
      OR (burst_count(request.key, last_1s) >= 10 AND response.status != 429)
      OR (minute_count(request.key, last_60s) >= 60 AND response.status != 429)
      OR (hour_count(request.key, last_3600s) >= 1000 AND response.status != 429)
      OR (response.status == 429 AND "Retry-After" NOT IN response.headers)
END FUNCTION
```

**Gap 5 — Exception Handler Formal Specification:**
```
FUNCTION isBugCondition_ExceptionHandler(exception, response)
  INPUT: exception of type DomainError, response of type HTTP Response
  OUTPUT: boolean

  RETURN (exception IS AccountLockedError AND response.status != 423)
      OR (request_id in error response != correlation_id_var.get())
END FUNCTION
```

**Gap 6 — Async I/O S3 Formal Specification:**
```
FUNCTION isBugCondition_AsyncIO_S3(adapter_method)
  INPUT: adapter_method = any async method in S3AvatarStorage
  OUTPUT: boolean

  RETURN adapter_method calls boto3.client("s3") synchronously
      -- i.e., uses synchronous I/O inside an async def, blocking the event loop
END FUNCTION
```

### Examples

**Gap 1:**
- Any response currently returns `X-XSS-Protection: 1; mode=block` → should be `0`
- Any response currently returns HSTS without `preload` → must include `preload`
- `GET /api/v1/profiles/me` response missing `Cache-Control` → must include `no-store, no-cache, must-revalidate`
- `GET /health` response includes `Server: uvicorn` → `Server` header must be removed
- Middleware references public `SECURITY_HEADERS` dict → must be renamed to `_SECURITY_HEADERS`

**Gap 2:**
- `DynamoDBProfileRepository.find_by_id()` with DynamoDB unavailable → raw `ClientError` propagates → should be `RepositoryError`
- `DynamoDBProfileRepository.save()` with duplicate PK → `ConditionalCheckFailedException` propagates → should be `RepositoryError`
- `DynamoDBProfileRepository.update()` with missing PK → `ConditionalCheckFailedException` propagates → should be `NotFoundError(user_message="Profile not found")`
- `DynamoDBProfileRepository.scan()` with throttling → raw `ClientError` propagates → should be `RepositoryError`

**Gap 3:**
- `await profile_repo.save(profile)` calls `self._table.put_item(...)` synchronously → blocks the event loop thread → under concurrent Lambda invocations, throughput degrades

**Gap 4:**
- User with JWT `sub=user-123` makes 61 requests/min from IP `1.2.3.4`, then switches to IP `5.6.7.8` → current code resets counter (IP-keyed) → should be blocked (sub-keyed)
- Any successful response missing `X-RateLimit-Remaining` header → must always be present
- 11 requests in 1 second → current code does not block → should return 429

**Gap 5:**
- `AccountLockedError` raised → not found in `_STATUS_MAP` → falls through to 500 handler → should return 423
- Domain exception handled → `request_id` read from `request.headers.get("X-Request-ID", "")` → diverges from `correlation_id_var` value set by `CorrelationIdMiddleware`

**Gap 6:**
- `await avatar_storage.upload(file)` calls `self._s3.put_object(...)` synchronously → blocks the event loop during avatar upload

---

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- Valid GET profile request continues to return profile data with 200 (3.1)
- Valid POST profile request continues to persist and return 201 (3.2)
- Valid PUT profile request continues to update and return updated data (3.3)
- Valid DELETE profile request continues to remove profile and return 204 (3.4)
- Profile not found continues to return 404 (3.5)
- Valid avatar upload continues to store in S3 and return the avatar URL (3.6)
- `GET /health` continues to return 200 without authentication (3.7)
- Requests exceeding 60 req/min continue to return 429 (3.8)
- Successful DynamoDB operations continue to return the correct domain entity (3.9)
- `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin` retain their current correct values (3.10)
- `ValidationError`, `NotFoundError`, `ConflictError`, `AuthenticationError`, `AuthorizationError` continue to return 422, 404, 409, 401, 403 respectively (3.11)

**Scope:**
All inputs that do NOT trigger one of the 20 bug conditions must be completely unaffected.
This includes all profile CRUD operations, avatar handling, health checks, and any request
that does not exercise the six defective code paths.

---

## Hypothesized Root Cause

**Gap 1 — Security Headers:**
The `SECURITY_HEADERS` dict was written before the platform contract Section 9.2 was finalized.
The four missing headers were added to the contract after the initial implementation. The `Server`
header removal, `Cache-Control` conditional, and private naming convention were never implemented.

**Gap 2 — DynamoDB ClientError Wrapping:**
The repository was implemented without following the repository pattern checklist. No
`try/except ClientError` blocks were added, and the `_raise_repository_error()` helper method
was never implemented. The `ConditionalCheckFailedException` mappings for `save()` and `update()`
were also omitted.

**Gap 3 — Async I/O DynamoDB:**
The repository was initially written with synchronous `boto3.resource("dynamodb")` calls inside
`async def` methods. This works functionally but blocks the event loop on every DynamoDB call.
The `aioboto3` dependency was not added when the repository was first implemented.

Note: Gap 2 (ClientError wrapping) must be applied to the existing `boto3` API first, then
Gap 3 (aioboto3 migration) replaces the sync client as a separate step.

**Gap 4 — Rate Limiting:**
The middleware was written as a minimal IP-based implementation. JWT sub extraction, multi-window
enforcement, and response headers were deferred and never completed.

**Gap 5 — Exception Handler:**
`AccountLockedError` was added to the domain exception hierarchy after the `_STATUS_MAP` was
initially written and was never added to the map. The `request_id` was read directly from the
incoming request header rather than from the `correlation_id_var` ContextVar, which is the
authoritative value set by `CorrelationIdMiddleware` for the current request lifecycle.

**Gap 6 — Async I/O S3:**
`S3AvatarStorage` was implemented with synchronous `boto3.client("s3")` calls inside `async def`
methods, mirroring the same pattern as the DynamoDB repository. The `aioboto3` dependency was
not added when the adapter was first implemented.

---

## Correctness Properties

Property 1: Fault Condition — Security Headers Completeness

_For any_ HTTP response returned by the fixed `SecurityHeadersMiddleware`, all 9 required headers
SHALL be present with their exact platform-contract values; the `Server` header SHALL be absent;
for any request path starting with `/api/`, `Cache-Control: no-store, no-cache, must-revalidate`
SHALL be present; and the headers dict SHALL be stored as the private `_SECURITY_HEADERS` attribute.

**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7**

Property 2: Fault Condition — ClientError Isolation

_For any_ DynamoDB operation in `DynamoDBProfileRepository` that raises a `ClientError`, the fixed
repository SHALL catch the exception and raise either a `RepositoryError` or `NotFoundError` —
never a raw `ClientError` — to the application layer.

**Validates: Requirements 2.8, 2.9, 2.10**

Property 3: Fault Condition — Non-Blocking DynamoDB I/O

_For any_ async method in the fixed `DynamoDBProfileRepository`, the implementation SHALL use
`aioboto3` with `async with session.client("dynamodb")` and SHALL NOT call any synchronous
`boto3.resource()` or `boto3.client()` function.

**Validates: Requirements 2.11**

Property 4: Fault Condition — Rate Limit Key Isolation

_For any_ two requests carrying different JWT `sub` values, the fixed `RateLimitMiddleware` SHALL
maintain independent rate limit counters for each `sub`, regardless of whether the requests
originate from the same IP address.

**Validates: Requirements 2.12, 2.13, 2.14**

Property 5: Fault Condition — Rate Limit Headers Always Present

_For any_ non-429 response, the fixed `RateLimitMiddleware` SHALL include `X-RateLimit-Limit`,
`X-RateLimit-Remaining`, and `X-RateLimit-Reset` headers. For any 429 response, it SHALL also
include `Retry-After`.

**Validates: Requirements 2.15, 2.16**

Property 6: Fault Condition — AccountLockedError Maps to 423

_For any_ `AccountLockedError` raised in the fixed service, the exception handler SHALL return
HTTP 423 by resolving `AccountLockedError` in `_STATUS_MAP` before falling through to the
generic 500 handler.

**Validates: Requirements 2.17**

Property 7: Fault Condition — Correlation ID Consistency

_For any_ domain exception handled by the fixed exception handler, the `request_id` included in
the error log and response SHALL equal the value of `correlation_id_var.get()` set by
`CorrelationIdMiddleware`, not the raw `X-Request-ID` request header.

**Validates: Requirements 2.18**

Property 8: Fault Condition — Non-Blocking S3 I/O

_For any_ async method in the fixed `S3AvatarStorage`, the implementation SHALL use `aioboto3`
with `async with session.client("s3")` and SHALL NOT call any synchronous `boto3.client()`
function.

**Validates: Requirements 2.19**

Property 9: Preservation — Existing Correct Headers Unchanged

_For any_ HTTP response where the bug condition does NOT hold (i.e., the response already had
correct header values), the fixed `SecurityHeadersMiddleware` SHALL continue to return
`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, and
`Referrer-Policy: strict-origin-when-cross-origin` with their current correct values.

**Validates: Requirements 3.10**

Property 10: Preservation — Successful DynamoDB Operations Return Domain Entity

_For any_ DynamoDB operation that succeeds (no `ClientError`), the fixed `DynamoDBProfileRepository`
SHALL return the same domain entity as the original repository, preserving all serialization behavior.

**Validates: Requirements 3.9**

Property 11: Preservation — Profile CRUD and Avatar Flow Regression

_For any_ valid profile operation (create → get → update → delete) or avatar upload, the fixed
service SHALL produce the same sequence of responses as the original service.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6**

Property 12: Preservation — Existing Exception Status Codes Unchanged

_For any_ `ValidationError`, `NotFoundError`, `ConflictError`, `AuthenticationError`, or
`AuthorizationError` raised in the fixed service, the exception handler SHALL continue to return
422, 404, 409, 401, and 403 respectively — unchanged from the original behavior.

**Validates: Requirements 3.11**

---

## Fix Implementation

### Gap 1 — Security Headers

**File**: `src/presentation/middleware/security_headers.py`

**Specific Changes:**
1. Rename the public `SECURITY_HEADERS` dict to `_SECURITY_HEADERS` (underscore-prefixed)
2. Replace the dict contents with the complete 9-header set per platform contract Section 9.2:
   - `X-XSS-Protection: 0`
   - `Strict-Transport-Security: max-age=31536000; includeSubDomains; preload`
   - `Content-Security-Policy: default-src 'none'; frame-ancestors 'none'`
   - Add `Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=()`
   - Add `Cross-Origin-Opener-Policy: same-origin`
   - Add `Cross-Origin-Resource-Policy: same-origin`
3. In `dispatch()`, after setting headers: `response.headers.pop("server", None)`
4. In `dispatch()`, add conditional: if `request.url.path.startswith("/api/")`, set `Cache-Control: no-store, no-cache, must-revalidate`

### Gap 2 — DynamoDB ClientError Wrapping

**File**: `src/infrastructure/persistence/dynamodb_profile_repository.py`

**Specific Changes:**
1. Add `from botocore.exceptions import ClientError` import
2. Add `_raise_repository_error(self, operation: str, e: ClientError) -> None` instance method — logs full error internally via structlog, raises `RepositoryError` with safe `user_message="An unexpected error occurred"`
3. Wrap every DynamoDB call (`put_item`, `get_item`, `scan`, `delete_item`) in `try/except ClientError`
4. In `save()`: catch `ConditionalCheckFailedException` → raise `RepositoryError(error_code="REPOSITORY_ERROR", user_message="An unexpected error occurred")`
5. In `update()`: catch `ConditionalCheckFailedException` → raise `NotFoundError(error_code="NOT_FOUND", user_message="Profile not found")`

Note: Apply Gap 2 to the existing `boto3` API first. Gap 3 (aioboto3 migration) is a separate
subsequent step that replaces the sync client while preserving the error handling added here.

### Gap 3 — Async I/O DynamoDB

**File**: `src/infrastructure/persistence/dynamodb_profile_repository.py`

**Specific Changes:**
1. Add `aioboto3` to `pyproject.toml` dependencies
2. Replace `boto3.resource("dynamodb", ...)` with `self._session = aioboto3.Session()` stored in `__init__`
3. Use `async with self._session.client("dynamodb", region_name=self._region) as client:` inside each async method
4. Update `__init__` signature: `(self, table_name: str, region: str, session: aioboto3.Session) -> None`
5. Update `src/main.py` to pass `session=aioboto3.Session()` when constructing `DynamoDBProfileRepository`
6. The existing `_to_item`/`_from_item` serialization (AttributeValue dicts) is preserved — no serialization changes required

### Gap 4 — Rate Limiting

**File**: `src/presentation/middleware/rate_limiting.py`

**Specific Changes:**
1. Replace any module-level counter dict with `self._counters: dict[str, list[float]] = defaultdict(list)` in `__init__`
2. Add `_extract_key(self, request: Request) -> str` method:
   - Decode Bearer JWT without signature verification, extract `sub` → return `f"user:{sub}"`
   - Fallback to `X-Forwarded-For` or `client.host` → return `f"ip:{ip}"`
3. Add three window constants: `_WINDOW_MINUTE=60.0`, `_WINDOW_HOUR=3600.0`, `_BURST_WINDOW=1.0`
4. Add three limit constants: `_MAX_PER_MINUTE=60`, `_MAX_PER_HOUR=1000`, `_MAX_BURST=10`
5. In `dispatch()`: prune `self._counters[key]` to 1-hour window; compute burst/minute/hour hit counts; return 429 with `Retry-After` if any limit exceeded
6. On non-429 responses: set `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset` headers

### Gap 5 — Exception Handler

**File**: `src/presentation/middleware/exception_handler.py`

**Specific Changes:**
1. Add `from src.domain.exceptions import AccountLockedError` import (if not already present)
2. Add `AccountLockedError: 423` entry to `_STATUS_MAP`
3. Replace `request_id = request.headers.get("X-Request-ID", "")` with `request_id = correlation_id_var.get("")` — import `correlation_id_var` from `src/presentation/middleware/correlation_id.py`

### Gap 6 — Async I/O S3

**File**: `src/infrastructure/adapters/s3_avatar_storage.py`

**Specific Changes:**
1. Replace `boto3.client("s3", ...)` with `self._session = aioboto3.Session()` stored in `__init__`
2. Use `async with self._session.client("s3", region_name=self._region) as client:` inside each async method
3. Update `__init__` signature: `(self, bucket_name: str, region: str, session: aioboto3.Session) -> None`
4. Update `src/main.py` to pass `session=aioboto3.Session()` when constructing `S3AvatarStorage`

---

## Testing Strategy

### Validation Approach

Two-phase approach: first surface counterexamples on unfixed code to confirm root cause analysis,
then verify the fix and preservation.

### Exploratory Fault Condition Checking

**Goal**: Surface counterexamples that demonstrate each bug BEFORE implementing the fix.

**Test Plan**: Write tests that exercise each defective code path and assert the correct behavior.
Run on UNFIXED code to observe failures and confirm root cause.

**Test Cases:**

1. **Security Headers — XSS header wrong** (will fail on unfixed code): Assert `X-XSS-Protection: 0` on any response
2. **Security Headers — missing Permissions-Policy** (will fail on unfixed code): Assert header present on any response
3. **Security Headers — Server header exposed** (will fail on unfixed code): Assert `server` not in response headers
4. **Security Headers — Cache-Control on /api/ path** (will fail on unfixed code): Assert header present for `GET /api/v1/profiles/me`
5. **Security Headers — public dict name** (will fail on unfixed code): Assert `_SECURITY_HEADERS` attribute exists (not `SECURITY_HEADERS`)
6. **ClientError leaks — put_item** (will fail on unfixed code): Mock boto3 to raise `ClientError` on `put_item`, assert `RepositoryError` raised
7. **ClientError leaks — get_item** (will fail on unfixed code): Mock boto3 to raise `ClientError` on `get_item`, assert `RepositoryError` raised
8. **ConditionalCheck mapping — save()** (will fail on unfixed code): Mock `ConditionalCheckFailedException`, assert `RepositoryError`
9. **ConditionalCheck mapping — update()** (will fail on unfixed code): Mock `ConditionalCheckFailedException`, assert `NotFoundError`
10. **Rate limit — IP-only keying** (will fail on unfixed code): Two requests with same sub, different IPs — assert shared counter
11. **Rate limit — burst window** (will fail on unfixed code): 11 requests in 1 second — assert 429
12. **Rate limit — missing headers** (will fail on unfixed code): Assert `X-RateLimit-Limit` present on 200 response
13. **Rate limit — missing Retry-After** (will fail on unfixed code): Exceed limit, assert `Retry-After` in 429 response
14. **AccountLockedError maps to 500** (will fail on unfixed code): Raise `AccountLockedError`, assert response status is 423 (currently 500)
15. **Correlation ID divergence** (will fail on unfixed code): Set `correlation_id_var`, raise domain exception, assert error log `request_id` matches ContextVar value
16. **S3 sync I/O** (will fail on unfixed code): Assert no `boto3.client("s3")` synchronous calls in `S3AvatarStorage` async methods

**Expected Counterexamples:**
- Security header assertions fail because `SECURITY_HEADERS` dict has wrong/missing values
- `ClientError` propagates because no `try/except` blocks exist in `DynamoDBProfileRepository`
- Rate limit counter is keyed by IP, not sub — different IPs bypass per-user limits
- `AccountLockedError` not in `_STATUS_MAP` — falls through to 500 handler
- `request_id` in error response comes from request header, not `correlation_id_var`

### Fix Checking

**Goal**: Verify that for all inputs where the bug condition holds, the fixed code produces the expected behavior.

**Pseudocode:**
```
FOR ALL response WHERE isBugCondition_SecurityHeaders(response) DO
  result := SecurityHeadersMiddleware_fixed.dispatch(request, response)
  ASSERT all 9 headers present with correct values
  ASSERT "server" NOT IN result.headers
  ASSERT (path STARTS_WITH "/api/" IMPLIES "Cache-Control" IN result.headers)
  ASSERT middleware uses _SECURITY_HEADERS (private attribute)
END FOR

FOR ALL operation WHERE isBugCondition_ClientError(ClientError, "application") DO
  result := DynamoDBProfileRepository_fixed.operation(...)
  ASSERT result IS RepositoryError OR result IS NotFoundError
  ASSERT result IS NOT ClientError
END FOR

FOR ALL method WHERE isBugCondition_AsyncIO_DynamoDB(method) DO
  ASSERT method uses aioboto3 async context manager
  ASSERT method does NOT call boto3.resource() synchronously
END FOR

FOR ALL request WHERE isBugCondition_RateLimit(request, response) DO
  result := RateLimitMiddleware_fixed.dispatch(request, call_next)
  ASSERT correct window enforced per sub (not IP)
  ASSERT rate limit headers present on all responses
  ASSERT Retry-After present on 429
END FOR

FOR ALL exception WHERE isBugCondition_ExceptionHandler(exception, response) DO
  result := exception_handler_fixed(request, exception)
  ASSERT AccountLockedError -> 423
  ASSERT request_id == correlation_id_var.get()
END FOR

FOR ALL method WHERE isBugCondition_AsyncIO_S3(method) DO
  ASSERT method uses aioboto3 async context manager
  ASSERT method does NOT call boto3.client("s3") synchronously
END FOR
```

### Preservation Checking

**Goal**: Verify that for all inputs where the bug condition does NOT hold, the fixed code produces the same result as the original.

**Pseudocode:**
```
FOR ALL response WHERE NOT isBugCondition_SecurityHeaders(response) DO
  -- specifically: X-Content-Type-Options, X-Frame-Options, Referrer-Policy unchanged
  ASSERT SecurityHeadersMiddleware_original(response) headers subset
      == SecurityHeadersMiddleware_fixed(response) headers subset
END FOR

FOR ALL operation WHERE NOT isBugCondition_ClientError(exception, layer) DO
  -- i.e., DynamoDB operation succeeds
  ASSERT DynamoDBProfileRepository_original.operation() == DynamoDBProfileRepository_fixed.operation()
END FOR

FOR ALL request WHERE NOT isBugCondition_RateLimit(request, response) DO
  -- i.e., request is within limits
  ASSERT response.status == original_response.status
END FOR

FOR ALL exception WHERE NOT isBugCondition_ExceptionHandler(exception, response) DO
  -- i.e., ValidationError/NotFoundError/ConflictError/AuthenticationError/AuthorizationError
  ASSERT exception_handler_original(request, exception).status
      == exception_handler_fixed(request, exception).status
END FOR
```

**Testing Approach**: Property-based testing is recommended for preservation checking because:
- It generates many request/response/exception combinations automatically
- It catches edge cases (unusual paths, header combinations, exception types) that manual tests miss
- It provides strong guarantees that behavior is unchanged for all non-buggy inputs

**Test Cases:**
1. **Correct headers unchanged**: `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy` values unchanged after security headers fix
2. **Successful DynamoDB round-trip**: save/find/update/delete on valid inputs returns same domain entity after ClientError wrapping fix
3. **Profile CRUD regression**: create → get → update → delete produces same responses before and after fix
4. **Avatar upload regression**: upload and retrieve avatar produces same S3 URL before and after fix
5. **Existing exception status codes**: `ValidationError`, `NotFoundError`, `ConflictError`, `AuthenticationError`, `AuthorizationError` continue to return 422, 404, 409, 401, 403
6. **Rate limit 429 still fires**: Requests exceeding 60/min still return 429 after rate limit fix

### Unit Tests

- `tests/unit/presentation/test_security_headers.py` — all 9 headers, Server removal, Cache-Control conditional, non-`/api/` path exclusion, private `_SECURITY_HEADERS` attribute
- `tests/unit/presentation/test_rate_limiting.py` — per-user keying, 3 windows, response headers, instance state isolation, IP fallback, Retry-After on 429
- `tests/unit/presentation/test_exception_handler.py` — `AccountLockedError` → 423, `correlation_id_var` used for request_id, existing exception mappings unchanged
- `tests/unit/infrastructure/test_dynamodb_profile_repository.py` — ClientError wrapping for all 4 operations, `ConditionalCheckFailedException` mapping for `save()` and `update()`, successful operation passthrough
- `tests/unit/infrastructure/test_s3_avatar_storage.py` — aioboto3 async context manager used, no synchronous boto3 calls, upload/retrieve behavior preserved

### Property-Based Tests

- Generate random HTTP paths and assert `Cache-Control` presence/absence based on `/api/` prefix
- Generate random `sub` values and assert rate limit counters are isolated per sub
- Generate random `DynamoDB ClientError` codes and assert all map to `RepositoryError` (except `ConditionalCheckFailedException` on `update()` which maps to `NotFoundError`)
- Generate random domain exception types and assert each maps to the correct HTTP status code
- Generate random valid profile payloads and assert `_to_item`/`_from_item` round-trip is preserved after aioboto3 migration

### Integration Tests

- `tests/integration/test_dynamodb_profile_repository.py` — moto-based: save/find/update/delete round-trips, `ConditionalCheckFailedException` scenarios, ClientError wrapping with mocked failures
- `tests/integration/test_s3_avatar_storage.py` — moto-based: upload/retrieve/delete avatar round-trip with aioboto3
- `tests/integration/test_profile_flow.py` — full create → get → update → delete flow with fixed service
