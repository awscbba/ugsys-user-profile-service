# Bugfix Requirements Document

## Introduction

The `ugsys-user-profile-service` service has six enterprise pattern compliance gaps that constitute security and reliability defects. These violations of the platform contract must be resolved before production deployment. The gaps span security headers, DynamoDB error handling, async I/O correctness, rate limiting, the exception handler mapping, and S3 async I/O.

---

## Bug Analysis

### Current Behavior (Defect)

**Security Headers (Section 9.2)**

1.1 WHEN any HTTP response is returned THEN the system sets `X-XSS-Protection: 1; mode=block`, which re-enables the legacy browser XSS filter that is known to introduce vulnerabilities

1.2 WHEN any HTTP response is returned THEN the system sets `Strict-Transport-Security: max-age=31536000; includeSubDomains` without the `preload` directive, preventing HSTS preload list inclusion

1.3 WHEN any HTTP response is returned THEN the system sets `Content-Security-Policy: default-src 'self'`, which is too permissive for a pure API service and does not include `frame-ancestors 'none'`

1.4 WHEN any HTTP response is returned THEN the system omits the `Permissions-Policy`, `Cross-Origin-Opener-Policy`, `Cross-Origin-Resource-Policy`, and `Cache-Control` headers required by the platform contract

1.5 WHEN any HTTP response is returned THEN the system includes the `Server` response header, exposing the technology stack to potential attackers

1.6 WHEN any HTTP response is returned THEN the system references a public `SECURITY_HEADERS` dict, inconsistent with the private naming convention used by the platform contract

**DynamoDB ClientError Wrapping**

1.7 WHEN a DynamoDB `put_item` call fails in `DynamoDBProfileRepository` THEN the system allows the raw `ClientError` to propagate to the unhandled exception handler, leaking infrastructure error details

1.8 WHEN a DynamoDB `get_item` call fails in `DynamoDBProfileRepository` THEN the system allows the raw `ClientError` to propagate to the unhandled exception handler

1.9 WHEN a DynamoDB `scan` call fails in `DynamoDBProfileRepository` THEN the system allows the raw `ClientError` to propagate to the unhandled exception handler

1.10 WHEN a DynamoDB `delete_item` call fails in `DynamoDBProfileRepository` THEN the system allows the raw `ClientError` to propagate to the unhandled exception handler

1.11 WHEN `DynamoDBProfileRepository.save()` encounters a `ConditionalCheckFailedException` THEN the system propagates the raw boto3 exception instead of raising a `RepositoryError`

1.12 WHEN `DynamoDBProfileRepository.update()` encounters a `ConditionalCheckFailedException` THEN the system propagates the raw boto3 exception instead of raising a `NotFoundError`

**Async I/O — DynamoDB**

1.13 WHEN `DynamoDBProfileRepository` performs any DynamoDB operation THEN the system uses synchronous `boto3.resource("dynamodb")` calls inside `async` methods, blocking the event loop and degrading throughput under concurrent load

**Rate Limiting**

1.14 WHEN an authenticated user makes requests THEN the system keys rate limiting only by IP address (`X-Forwarded-For` / `client.host`), not by JWT `sub`, allowing a single user to bypass per-user limits from multiple IPs

1.15 WHEN a request is made THEN the system enforces only a 60 req/min window and does not enforce the 1000 req/hour or 10 req/second burst limits required by the platform contract

1.16 WHEN a request is processed or rate-limited THEN the system omits the `X-RateLimit-Limit`, `X-RateLimit-Remaining`, and `X-RateLimit-Reset` response headers

1.17 WHEN a 429 response is returned THEN the system omits the `Retry-After` header required by the platform contract

**Exception Handler**

1.18 WHEN an `AccountLockedError` is raised THEN the system does not find a matching entry in `_STATUS_MAP` and falls through to the generic 500 handler instead of returning HTTP 423

1.19 WHEN a domain exception is handled THEN the system reads `request_id` from `request.headers.get("X-Request-ID", "")` rather than from the `correlation_id_var` ContextVar, causing the request ID in error responses to diverge from the one set by `CorrelationIdMiddleware`

**Async I/O — S3**

1.20 WHEN `S3AvatarStorage` performs any S3 operation THEN the system uses synchronous `boto3.client("s3")` calls inside `async` methods, blocking the event loop during avatar upload and retrieval

---

### Expected Behavior (Correct)

**Security Headers (Section 9.2)**

2.1 WHEN any HTTP response is returned THEN the system SHALL set `X-XSS-Protection: 0` to disable the legacy XSS filter and rely on CSP instead

2.2 WHEN any HTTP response is returned THEN the system SHALL set `Strict-Transport-Security: max-age=31536000; includeSubDomains; preload`

2.3 WHEN any HTTP response is returned THEN the system SHALL set `Content-Security-Policy: default-src 'none'; frame-ancestors 'none'`

2.4 WHEN any HTTP response is returned THEN the system SHALL include `Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=()`, `Cross-Origin-Opener-Policy: same-origin`, and `Cross-Origin-Resource-Policy: same-origin`

2.5 WHEN a request path matches `/api/*` THEN the system SHALL include `Cache-Control: no-store, no-cache, must-revalidate`

2.6 WHEN any HTTP response is returned THEN the system SHALL remove the `Server` response header

2.7 WHEN the security headers middleware is implemented THEN the system SHALL store the headers dict as a private attribute (underscore-prefixed) consistent with the platform contract naming convention

**DynamoDB ClientError Wrapping**

2.8 WHEN any DynamoDB operation fails in `DynamoDBProfileRepository` THEN the system SHALL catch `ClientError`, log the full error detail internally via `_raise_repository_error()`, and raise a `RepositoryError` with a safe `user_message`

2.9 WHEN `DynamoDBProfileRepository.save()` encounters a `ConditionalCheckFailedException` THEN the system SHALL raise a `RepositoryError` with `error_code="REPOSITORY_ERROR"` and `user_message="An unexpected error occurred"`

2.10 WHEN `DynamoDBProfileRepository.update()` encounters a `ConditionalCheckFailedException` THEN the system SHALL raise a `NotFoundError` with `error_code="NOT_FOUND"` and `user_message="Profile not found"`

**Async I/O — DynamoDB**

2.11 WHEN `DynamoDBProfileRepository` performs any DynamoDB operation THEN the system SHALL use `aioboto3` with `async with session.client("dynamodb")` so that I/O does not block the event loop

**Rate Limiting**

2.12 WHEN an authenticated request carries a valid JWT THEN the system SHALL extract the `sub` claim and key rate limiting by that value instead of by IP address

2.13 WHEN an unauthenticated request is received THEN the system SHALL fall back to IP-based rate limiting

2.14 WHEN any request is processed THEN the system SHALL enforce a 60 req/min window, a 1000 req/hour window, and a 10 req/second burst limit

2.15 WHEN any response is returned THEN the system SHALL include `X-RateLimit-Limit`, `X-RateLimit-Remaining`, and `X-RateLimit-Reset` headers

2.16 WHEN a 429 response is returned THEN the system SHALL include a `Retry-After` header

**Exception Handler**

2.17 WHEN an `AccountLockedError` is raised THEN the system SHALL return HTTP 423 by including `AccountLockedError: 423` in `_STATUS_MAP`

2.18 WHEN a domain exception is handled THEN the system SHALL read the request ID from the `correlation_id_var` ContextVar set by `CorrelationIdMiddleware` so that the ID in error responses matches the one propagated through the request lifecycle

**Async I/O — S3**

2.19 WHEN `S3AvatarStorage` performs any S3 operation THEN the system SHALL use `aioboto3` with `async with session.client("s3")` so that avatar I/O does not block the event loop

---

### Unchanged Behavior (Regression Prevention)

3.1 WHEN a valid request to retrieve a user profile is made THEN the system SHALL CONTINUE TO return the profile data with a 200 response

3.2 WHEN a valid request to create a user profile is made THEN the system SHALL CONTINUE TO persist the profile and return a 201 response

3.3 WHEN a valid request to update a user profile is made THEN the system SHALL CONTINUE TO update the profile and return the updated data

3.4 WHEN a valid request to delete a user profile is made THEN the system SHALL CONTINUE TO remove the profile and return a 204 response

3.5 WHEN a profile is not found THEN the system SHALL CONTINUE TO return a 404 response

3.6 WHEN a valid avatar upload request is made THEN the system SHALL CONTINUE TO store the avatar in S3 and return the avatar URL

3.7 WHEN a request is made to `/health` THEN the system SHALL CONTINUE TO return a 200 response without requiring authentication

3.8 WHEN a request exceeds the 60 req/min limit THEN the system SHALL CONTINUE TO return a 429 response

3.9 WHEN a DynamoDB operation succeeds THEN the system SHALL CONTINUE TO return the correct domain entity to the caller

3.10 WHEN `X-Content-Type-Options`, `X-Frame-Options`, and `Referrer-Policy` headers are evaluated THEN the system SHALL CONTINUE TO return their current correct values (`nosniff`, `DENY`, `strict-origin-when-cross-origin`)

3.11 WHEN a `ValidationError`, `NotFoundError`, `ConflictError`, `AuthenticationError`, or `AuthorizationError` is raised THEN the system SHALL CONTINUE TO return the correct HTTP status code (422, 404, 409, 401, 403 respectively)
