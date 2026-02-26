# Requirements Document

## Introduction

The `ugsys-user-profile-service` currently has four enterprise-pattern gaps that create reliability, correctness, and maintainability risks:

1. **EventBridge async I/O** — the publisher uses synchronous `boto3` inside `async def publish()`, blocking the event loop on every event publish and degrading Lambda concurrency.
2. **Silent event loss** — publish failures have no `try/except` at all; any exception is silently swallowed and the caller never knows the event was not delivered. There is also no check on `FailedEntryCount` in the `put_events` response.
3. **Missing Lambda consumer entry point** — `event_consumer.py` contains the routing logic but there is no `main_consumer.py` Lambda handler. The consumer cannot be deployed as a Lambda function.
4. **Structural debt** — request DTOs are defined inline in the router file, `ProfileResponse` serialization is a private helper function rather than a proper DTO, and `ProfileService` has no inbound port interface, making the presentation layer depend on the concrete class.

This spec covers the aioboto3 migration for the EventBridge publisher, error propagation hardening, the Lambda consumer entry point, application DTO extraction, `ProfileResponse` DTO, and the `IProfileService` inbound port interface.

> **Out of scope**: Outbox pattern, Unit of Work, Circuit Breaker, S3 avatar async migration, and DynamoDB `ClientError` wrapping are explicitly excluded — they are either not needed for this service or covered by the `user-profile-hardening` bugfix spec.

---

## Glossary

- **EventBridgePublisher**: The infrastructure adapter in `src/infrastructure/messaging/event_publisher.py` that publishes domain events to the AWS EventBridge custom bus `ugsys-event-bus`.
- **EventPublisher**: The domain port (ABC) in `src/domain/repositories/event_publisher.py` that `EventBridgePublisher` implements.
- **aioboto3**: The async wrapper around `boto3` that provides non-blocking AWS SDK calls compatible with Python's `asyncio` event loop.
- **FailedEntryCount**: A field in the `put_events` response that indicates how many entries failed to be delivered to EventBridge. A value greater than zero means partial or total delivery failure.
- **ExternalServiceError**: The domain exception defined in `src/domain/exceptions.py` raised when an external service call fails. HTTP 502.
- **event_consumer**: The module `src/infrastructure/messaging/event_consumer.py` containing `handle_event()` and the per-event-type handler functions.
- **main_consumer**: The Lambda entry point module `src/main_consumer.py` that wires all dependencies and invokes `handle_event()` via `asyncio.run()`.
- **Lambda handler**: A Python function with signature `def lambda_handler(event: dict, context: Any) -> dict` that AWS Lambda invokes directly.
- **EventBridge envelope**: The outer structure of an EventBridge event delivered to a Lambda consumer, containing fields `detail-type` and `detail`. The `detail` field contains the publisher's envelope, which in turn contains a `payload` field with the actual domain event data.
- **ProfileService**: The application service in `src/application/services/profile_service.py` that orchestrates all profile operations.
- **IProfileService**: The inbound port interface (ABC) for `ProfileService`, to be defined in `src/application/interfaces/profile_service.py`.
- **ProfileResponse**: A Pydantic response DTO to be defined in `src/application/dtos/profile_dtos.py` with a `from_domain(profile: UserProfile) -> ProfileResponse` class method, replacing the `_profile_dict()` helper in the router.
- **profile_dtos**: The module `src/application/dtos/profile_dtos.py` that will contain all request and response DTOs for the profiles domain.
- **UserProfile**: The domain entity in `src/domain/entities/profile.py` representing a user's profile.

---

## Requirements

### Requirement 1: EventBridge Async I/O

**User Story:** As a platform engineer, I want the EventBridge publisher to use non-blocking async I/O, so that Lambda concurrency is not degraded by synchronous network calls inside async handlers.

#### Acceptance Criteria

1. THE `EventBridgePublisher` SHALL use `aioboto3` to create an async EventBridge client, replacing the synchronous `boto3.client("events")` instantiation.
2. WHEN `EventBridgePublisher.publish()` is called, THE `EventBridgePublisher` SHALL call `put_events` via the async aioboto3 client using `await`, not a synchronous call.
3. THE `EventBridgePublisher` SHALL manage the aioboto3 client lifecycle using an async context manager (`async with session.client(...)`) consistent with the pattern used for the DynamoDB client in `src/main.py`.
4. THE `EventBridgePublisher` constructor SHALL accept an `aioboto3.Session` instance as a dependency rather than creating its own session, enabling injection and testability.

---

### Requirement 2: EventBridge Error Propagation

**User Story:** As a platform engineer, I want publish failures to surface as exceptions rather than being silently swallowed, so that callers can decide whether to retry or alert.

#### Acceptance Criteria

1. WHEN `EventBridgePublisher.publish()` raises any exception from the aioboto3 client, THE `EventBridgePublisher` SHALL log the error with `structlog` at `error` level including `detail_type` and `error` fields, then raise an `ExternalServiceError` with `user_message="An unexpected error occurred"`.
2. THE `EventBridgePublisher` SHALL NOT catch exceptions and return normally — the current absence of error handling MUST be replaced with an explicit `try/except` block that always re-raises as `ExternalServiceError`.
3. WHEN `put_events` returns a response where `FailedEntryCount > 0`, THE `EventBridgePublisher` SHALL raise an `ExternalServiceError` with the failed entry details in the internal `message` and `user_message="An unexpected error occurred"`.
4. WHEN `EventBridgePublisher.publish()` succeeds with `FailedEntryCount == 0`, THE `EventBridgePublisher` SHALL log at `info` level with `detail_type` and `event_id` fields, consistent with the current success log.

---

### Requirement 3: Lambda Consumer Entry Point

**User Story:** As a platform engineer, I want a deployable Lambda handler entry point for the event consumer, so that the service can receive and process EventBridge events from the identity-manager.

#### Acceptance Criteria

1. THE `main_consumer` module SHALL be defined at `src/main_consumer.py` as a standalone Lambda handler, separate from the main FastAPI application in `src/main.py`.
2. THE `main_consumer` module SHALL define a `lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]` function that AWS Lambda can invoke directly.
3. WHEN `lambda_handler` is invoked, THE `main_consumer` SHALL wire all required dependencies: an `aioboto3.Session`, a DynamoDB async client, an S3 async client, the `DynamoDBProfileRepository`, the `S3AvatarRepository`, the `EventBridgePublisher`, and the `ProfileService`.
4. WHEN `lambda_handler` is invoked, THE `main_consumer` SHALL extract the `payload` field from inside `event["detail"]` to obtain the domain event data, then pass the reconstructed event dict (with `detail-type` and `detail` set to the payload) to `handle_event()`.
5. WHEN `lambda_handler` is invoked, THE `main_consumer` SHALL call `handle_event(event, service)` via `asyncio.run()`.
6. WHEN `handle_event()` completes without raising, THE `main_consumer` SHALL return `{"statusCode": 200, "body": "OK"}`.
7. WHEN `handle_event()` raises an exception, THE `main_consumer` SHALL log the error at `error` level with `error` and `detail_type` fields, then re-raise the exception so Lambda marks the invocation as failed and triggers retry/DLQ behavior.
8. THE `main_consumer` module SHALL call `configure_logging(settings.service_name)` before processing any event, consistent with the logging standard.

---

### Requirement 4: Application DTOs Extraction

**User Story:** As a developer, I want all request DTOs extracted to `src/application/dtos/profile_dtos.py`, so that the presentation layer depends on stable, reusable data contracts rather than inline Pydantic models defined in the router file.

#### Acceptance Criteria

1. THE `UpdateContactRequest` DTO SHALL be defined in `src/application/dtos/profile_dtos.py` with fields: `phone: str | None`, `street: str | None`, `city: str | None`, `state: str | None`, `postal_code: str | None`, `country: str | None` — all optional, matching the current inline definition.
2. THE `UpdatePersonalRequest` DTO SHALL be defined in `src/application/dtos/profile_dtos.py` with fields: `full_name: str | None`, `date_of_birth: str | None` — all optional.
3. THE `UpdatePreferencesRequest` DTO SHALL be defined in `src/application/dtos/profile_dtos.py` with fields: `notification_preferences_email: bool | None`, `notification_preferences_sms: bool | None`, `notification_preferences_whatsapp: bool | None`, `language: str | None`, `timezone: str | None` — all optional.
4. THE `UpdateDisplayRequest` DTO SHALL be defined in `src/application/dtos/profile_dtos.py` with fields: `bio: str | None`, `display_name: str | None` — all optional.
5. WHEN the DTOs are extracted, THE router file `src/presentation/api/v1/profiles.py` SHALL import all four request DTOs from `src/application/dtos/profile_dtos` and SHALL NOT define any Pydantic request models inline.

---

### Requirement 5: ProfileResponse DTO

**User Story:** As a developer, I want a `ProfileResponse` DTO with a `from_domain()` class method, so that domain-to-response serialization is a first-class, testable concern rather than a private helper function in the router.

#### Acceptance Criteria

1. THE `ProfileResponse` DTO SHALL be defined in `src/application/dtos/profile_dtos.py` as a Pydantic `BaseModel` with fields that mirror all public attributes of the `UserProfile` domain entity: `user_id: str`, `email: str`, `full_name: str`, `phone: str | None`, `date_of_birth: str | None`, `address: AddressResponse`, `email_verified: bool`, `avatar_url: str | None`, `bio: str | None`, `display_name: str | None`, `language: str`, `timezone: str`, `notification_preferences: NotificationPreferencesResponse`, `deleted_at: str | None`.
2. THE `ProfileResponse` SHALL define a `from_domain(profile: UserProfile) -> ProfileResponse` class method that constructs a `ProfileResponse` from a `UserProfile` domain entity.
3. WHEN `ProfileResponse.from_domain(profile)` is called, THE `ProfileResponse` SHALL set `user_id` to `str(profile.user_id)` and map all other fields from the corresponding `UserProfile` attributes.
4. WHEN `ProfileResponse.from_domain(profile)` is called, THE `ProfileResponse` SHALL set `deleted_at` to `profile.deleted_at.isoformat()` if `profile.deleted_at` is not `None`, otherwise `None`.
5. THE router file `src/presentation/api/v1/profiles.py` SHALL replace all calls to `_profile_dict(profile)` with `ProfileResponse.from_domain(profile).model_dump()` and SHALL remove the `_profile_dict()` helper function.

---

### Requirement 6: IProfileService Inbound Port Interface

**User Story:** As a developer, I want an `IProfileService` ABC defined in `src/application/interfaces/profile_service.py`, so that the presentation layer depends on an abstraction and `ProfileService` is independently testable via mocks.

#### Acceptance Criteria

1. THE `IProfileService` ABC SHALL be defined in `src/application/interfaces/profile_service.py` with abstract async methods for every public method currently on `ProfileService`: `get_profile`, `create_profile`, `update_contact`, `update_personal`, `delete_profile`, `upload_avatar`, `delete_avatar`, `update_preferences`, `update_display`, `list_profiles`, `soft_delete_profile`, `get_profile_by_id`, `deactivate_profile`, `clear_password_change_flag`.
2. THE `IProfileService` ABC SHALL import ONLY from `src/domain/` and `src/application/commands/`, `src/application/queries/` — never from `src/infrastructure/` or `src/presentation/`.
3. THE `IProfileService` abstract method signatures SHALL match the concrete `ProfileService` method signatures exactly, including parameter names, type annotations, and return types.

---

### Requirement 7: ProfileService Implements IProfileService

**User Story:** As a developer, I want `ProfileService` to declare `class ProfileService(IProfileService)`, so that the interface contract is enforced by Python's ABC mechanism at instantiation time.

#### Acceptance Criteria

1. THE concrete `ProfileService` class SHALL declare `class ProfileService(IProfileService)`, inheriting from the ABC.
2. THE router file `src/presentation/api/v1/profiles.py` SHALL type-annotate the injected service as `IProfileService`, not as the concrete `ProfileService` class.
3. THE `get_profile_service()` dependency function in `src/presentation/api/v1/profiles.py` SHALL have return type `IProfileService`.
4. IF `ProfileService` is missing any abstract method declared in `IProfileService`, THEN Python SHALL raise a `TypeError` at instantiation time — this is the enforcement mechanism and SHALL be verified by a unit test that instantiates `ProfileService`.

---

### Requirement 8: Correctness Properties

**User Story:** As a platform engineer, I want property-based tests covering the reliability and correctness guarantees of the publisher, consumer, and DTO layer, so that regressions in these critical behaviors are caught automatically.

#### Acceptance Criteria

1. FOR ALL `put_events` responses where `FailedEntryCount > 0`, WHEN `EventBridgePublisher.publish()` processes the response, THE `EventBridgePublisher` SHALL raise `ExternalServiceError` — verified by generating arbitrary `FailedEntryCount` values greater than zero and asserting the exception is always raised (publisher failure invariant).
2. FOR ALL exceptions raised by the aioboto3 client during `put_events`, WHEN `EventBridgePublisher.publish()` is called, THE `EventBridgePublisher` SHALL raise `ExternalServiceError` and SHALL NOT return normally — verified by injecting arbitrary exceptions and asserting they are always re-raised as `ExternalServiceError` (error propagation invariant).
3. FOR ALL concrete classes that inherit from `IProfileService`, WHEN the class is instantiated, THE Python ABC mechanism SHALL enforce that all abstract methods declared in `IProfileService` are implemented — verified by asserting `ProfileService()` does not raise `TypeError` and that a stub class missing any method does raise `TypeError` (interface compliance invariant).
4. FOR ALL `UserProfile` domain entities, WHEN `ProfileResponse.from_domain(profile)` is called, THE `ProfileResponse` SHALL produce a model where `user_id == str(profile.user_id)` and `email == profile.email` and `full_name == profile.full_name` — verified across arbitrary `UserProfile` instances (DTO mapping invariant).
5. FOR ALL `identity.user.registered` events where a profile already exists (causing `ProfileService.create_profile()` to raise `ConflictError`), WHEN `handle_event()` is called, THE `event_consumer` SHALL complete without raising any exception — verified by generating arbitrary user IDs and asserting idempotent behavior (consumer idempotency invariant).
6. FOR ALL events with a `detail-type` value not in `{"identity.user.registered", "identity.user.deactivated", "identity.auth.password_changed"}`, WHEN `handle_event()` is called, THE `event_consumer` SHALL complete without raising any exception — verified by generating arbitrary string values for `detail-type` (unknown event robustness invariant).
