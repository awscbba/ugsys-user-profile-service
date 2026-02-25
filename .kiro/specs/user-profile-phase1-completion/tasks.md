# Implementation Plan: User Profile Service Phase 1 Completion

## Overview

Close all remaining P0/P1/P2 gaps in `ugsys-user-profile-service` following testability-first ordering: domain layer (pure Python, zero deps) first, then application layer (mockable ports), then infrastructure adapters (moto), then presentation layer (TestClient). Each task includes test sub-tasks following TDD workflow. The service already has basic CRUD, DynamoDB persistence, EventBridge publishing, and all three middleware — these tasks cover only the gaps.

## Tasks

- [ ] 1. Domain exception hierarchy and value objects
  - [ ] 1.1 Create domain exception hierarchy in `src/domain/exceptions.py`
    - Implement `DomainError` base with `message`, `user_message`, `error_code`, `additional_data`
    - Implement `ValidationError`, `NotFoundError`, `ConflictError`, `AuthorizationError`, `RepositoryError`, `ExternalServiceError`
    - _Requirements: 2.1_

  - [ ]* 1.2 Write unit tests for domain exceptions in `tests/unit/domain/test_exceptions.py`
    - Test each exception type has correct default `error_code`
    - Test `message` and `user_message` are stored separately
    - Test `DomainError` is an `Exception` subclass
    - _Requirements: 2.1_

  - [ ] 1.3 Create NotificationPreferences value object in `src/domain/value_objects/notification_preferences.py`
    - Implement as `@dataclass(frozen=True)` with `email=True`, `sms=False`, `whatsapp=False`
    - _Requirements: 1.7_

  - [ ]* 1.4 Write unit tests for NotificationPreferences in `tests/unit/domain/test_notification_preferences.py`
    - Test default values: `email=True`, `sms=False`, `whatsapp=False`
    - Test immutability: setting any attribute raises `FrozenInstanceError`
    - _Requirements: 1.7_

  - [ ]* 1.5 Write property test for NotificationPreferences in `tests/property/test_notification_preferences_props.py`
    - **Property 5: NotificationPreferences immutability**
    - **Validates: Requirements 1.7**

- [ ] 2. UserProfile entity extensions and new domain methods
  - [ ] 2.1 Extend UserProfile entity with new fields in `src/domain/entities/user_profile.py`
    - Add fields: `notification_preferences` (NotificationPreferences, default factory), `language` (str, default `"es"`), `timezone` (str, default `"America/La_Paz"`), `avatar_url` (str | None, default None), `bio` (str | None, default None, max 500), `display_name` (str | None, default None), `deleted_at` (datetime | None, default None)
    - _Requirements: 1.1, 1.2_

  - [ ] 2.2 Implement new entity methods: `update_preferences()`, `update_display()`, `soft_delete()`
    - `update_preferences()`: accepts optional `notification_preferences`, `language`, `timezone`; updates only provided fields; sets `updated_at`
    - `update_display()`: accepts optional `bio`, `display_name`; truncates bio to 500 chars; sets `updated_at`
    - `soft_delete()`: sets `deleted_at` to current UTC timestamp; sets `updated_at`
    - _Requirements: 1.3, 1.4, 1.5, 1.6_

  - [ ]* 2.3 Write unit tests for UserProfile entity extensions in `tests/unit/domain/test_profile_entity.py`
    - Test all new field defaults on fresh UserProfile creation
    - Test `update_preferences()` updates only provided fields
    - Test `update_display()` updates only provided fields
    - Test `update_display()` truncates bio > 500 chars to exactly 500
    - Test `soft_delete()` sets `deleted_at` to approximately current UTC
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6_

  - [ ]* 2.4 Write property tests for UserProfile entity in `tests/property/test_profile_entity_props.py`
    - **Property 1: UserProfile defaults are correct**
    - **Validates: Requirements 1.1, 1.2**
    - **Property 2: Partial update methods only change provided fields**
    - **Validates: Requirements 1.3, 1.4**
    - **Property 3: soft_delete sets deleted_at**
    - **Validates: Requirements 1.5**
    - **Property 4: Bio truncation at entity level**
    - **Validates: Requirements 1.6**

- [ ] 3. Domain ports (ABCs) for new infrastructure adapters
  - [ ] 3.1 Create EventPublisher ABC in `src/domain/repositories/event_publisher.py`
    - Define `publish(detail_type: str, payload: dict[str, Any]) -> None` abstract method
    - _Requirements: 3.3_

  - [ ] 3.2 Create AvatarStorage ABC in `src/domain/repositories/avatar_storage.py`
    - Define `upload(user_id: UUID, file_bytes: bytes, extension: str) -> str` (returns avatar URL)
    - Define `delete(user_id: UUID, extension: str) -> None`
    - _Requirements: 7.1, 7.5_

  - [ ] 3.3 Extend ProfileRepository ABC with `list_profiles(page, page_size) -> tuple[list[UserProfile], int]`
    - Returns (profiles_page, total_count), excludes soft-deleted profiles
    - _Requirements: 9.4_

- [ ] 4. Checkpoint — Domain layer complete
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 5. Application layer — New command/query DTOs
  - [ ] 5.1 Create new command DTOs in `src/application/commands/`
    - `UploadAvatarCommand`: user_id, requester_id, is_admin, file_bytes, content_type
    - `DeleteAvatarCommand`: user_id, requester_id, is_admin
    - `UpdatePreferencesCommand`: user_id, requester_id, is_admin, notification_preferences?, language?, timezone?
    - `UpdateDisplayCommand`: user_id, requester_id, is_admin, bio?, display_name?
    - `SoftDeleteProfileCommand`: user_id, requester_id
    - _Requirements: 7.1, 8.1, 12.1, 12.2, 10.1_

  - [ ] 5.2 Create ListProfilesQuery in `src/application/queries/`
    - `ListProfilesQuery`: requester_id, is_admin, page (default 1), page_size (default 20)
    - _Requirements: 9.1, 9.2_

- [ ] 6. Application layer — ProfileService modifications and new methods
  - [ ] 6.1 Migrate ProfileService to domain exceptions
    - Replace all `ValueError` raises with `NotFoundError` (profile not found) and `ConflictError` (duplicate profile)
    - Replace all `PermissionError` raises with `AuthorizationError` (IDOR violations)
    - Add `avatar_storage: AvatarStorage` constructor dependency
    - Change `event_publisher` type from `EventPublisherProtocol` to `EventPublisher` ABC
    - Add `duration_ms` performance logging to all service methods
    - _Requirements: 2.2, 2.3, 2.4_

  - [ ]* 6.2 Write unit tests for domain exception migration in `tests/unit/application/test_profile_service.py`
    - Test non-existent profile raises `NotFoundError` (not `ValueError`)
    - Test duplicate profile raises `ConflictError` (not `ValueError`)
    - Test IDOR violation raises `AuthorizationError` (not `PermissionError`)
    - _Requirements: 2.2, 2.3, 2.4_

  - [ ]* 6.3 Write property test for domain exception types in `tests/property/test_profile_service_props.py`
    - **Property 6: ProfileService raises correct domain exceptions**
    - **Validates: Requirements 2.2, 2.3, 2.4**

  - [ ] 6.4 Implement `upload_avatar()` and `delete_avatar()` in ProfileService
    - `upload_avatar(cmd)`: validate content_type (JPEG/PNG/WebP), validate size ≤ 5MB, IDOR check, call `AvatarStorage.upload()`, set `avatar_url`, persist, publish `profile.avatar_updated`
    - `delete_avatar(cmd)`: IDOR check, call `AvatarStorage.delete()`, set `avatar_url=None`, persist (no error if no avatar)
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8, 8.1, 8.2, 8.3_

  - [ ]* 6.5 Write unit tests for avatar operations in `tests/unit/application/test_profile_service.py`
    - Test valid JPEG upload sets avatar_url and publishes event
    - Test invalid content type raises `ValidationError` with correct message
    - Test oversized file raises `ValidationError` with correct message
    - Test avatar delete sets avatar_url to None
    - Test avatar delete when no avatar exists succeeds silently
    - Test IDOR check on avatar upload/delete
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.6, 7.8, 8.1, 8.2, 8.3_

  - [ ]* 6.6 Write property tests for avatar operations in `tests/property/test_profile_service_props.py`
    - **Property 14: Avatar upload sets avatar_url on profile**
    - **Validates: Requirements 7.1**
    - **Property 15: Invalid avatar files are rejected**
    - **Validates: Requirements 7.2, 7.3**
    - **Property 17: Avatar delete clears avatar_url**
    - **Validates: Requirements 8.1, 8.2**

  - [ ] 6.7 Implement `update_preferences()` and `update_display()` in ProfileService
    - `update_preferences(cmd)`: IDOR check, call `profile.update_preferences()`, persist, publish `profile.updated` with changed_fields
    - `update_display(cmd)`: IDOR check, validate bio ≤ 500 chars (raise `ValidationError`), call `profile.update_display()`, persist, publish `profile.updated` with changed_fields
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5_

  - [ ]* 6.8 Write unit tests for preferences and display updates in `tests/unit/application/test_profile_service.py`
    - Test preferences update persists and publishes event with changed_fields
    - Test display update persists and publishes event with changed_fields
    - Test bio > 500 chars raises `ValidationError` with correct message
    - Test IDOR check on preferences/display update
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5_

  - [ ]* 6.9 Write property test for bio API validation in `tests/property/test_profile_service_props.py`
    - **Property 23: Bio validation at API level rejects > 500 chars**
    - **Validates: Requirements 12.5**

  - [ ] 6.10 Implement `list_profiles()` and `soft_delete_profile()` in ProfileService
    - `list_profiles(query)`: verify admin, cap page_size at 100, delegate to `repo.list_profiles()`
    - `soft_delete_profile(cmd)`: verify admin, find profile, call `profile.soft_delete()`, persist, publish `profile.deleted`
    - _Requirements: 9.1, 9.2, 9.3, 9.6, 9.7, 10.1, 10.2, 10.3, 10.4, 10.5_

  - [ ]* 6.11 Write unit tests for admin operations in `tests/unit/application/test_profile_service.py`
    - Test list_profiles returns paginated result with metadata
    - Test page_size > 100 is capped at 100
    - Test non-admin raises `AuthorizationError` for list and soft-delete
    - Test soft-delete sets deleted_at and publishes `profile.deleted`
    - Test soft-delete on non-existent profile raises `NotFoundError`
    - _Requirements: 9.1, 9.2, 9.3, 9.6, 10.1, 10.2, 10.3, 10.5_

  - [ ]* 6.12 Write property tests for admin operations in `tests/property/test_profile_service_props.py`
    - **Property 18: Paginated list respects page_size with capping**
    - **Validates: Requirements 9.1, 9.2, 9.3**
    - **Property 19: Admin-only endpoints reject non-admin users**
    - **Validates: Requirements 9.6, 10.3**

  - [ ]* 6.13 Write property test for event publishing in `tests/property/test_profile_service_props.py`
    - **Property 9: Profile mutations publish correct events**
    - **Validates: Requirements 3.4, 7.6, 10.5, 12.4**

- [ ] 7. Application layer — Event consumer logic
  - [ ] 7.1 Implement event consumer handler in `src/infrastructure/messaging/event_consumer.py`
    - Lambda handler function with `match` on `detail-type`
    - `identity.user.registered`: extract user_id/email/full_name, create profile with defaults, skip if exists
    - `identity.user.deactivated`: find profile, call `soft_delete()`, persist, skip if not found
    - `identity.auth.password_changed`: find profile, call `clear_password_change_flag()`, persist, skip if not found
    - Validate required fields, log errors/warnings, never raise on missing data
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 5.1, 5.2, 5.3, 6.1, 6.2_

  - [ ]* 7.2 Write unit tests for event consumer in `tests/unit/application/test_event_consumer.py`
    - Test `identity.user.registered` creates profile with correct defaults
    - Test duplicate registration logs warning and skips
    - Test missing required fields logs error and skips
    - Test `identity.user.deactivated` soft-deletes profile
    - Test deactivation with non-existent profile logs warning and skips
    - Test `identity.auth.password_changed` clears flag
    - Test password_changed with non-existent profile logs warning and skips
    - Test unknown event type logs warning
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 5.1, 5.2, 5.3, 6.1, 6.2_

  - [ ]* 7.3 Write property tests for event consumer in `tests/property/test_event_consumer_props.py`
    - **Property 10: Event consumer creates profile with correct defaults on registration**
    - **Validates: Requirements 4.1, 4.2**
    - **Property 11: Event consumer is idempotent for duplicate registration**
    - **Validates: Requirements 4.3**
    - **Property 12: Event consumer soft-deletes on deactivation**
    - **Validates: Requirements 5.1**
    - **Property 13: Event consumer clears password change flag**
    - **Validates: Requirements 6.1**

- [ ] 8. Checkpoint — Application layer complete
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 9. Infrastructure layer — DynamoDB adapter extensions
  - [ ] 9.1 Extend DynamoDBProfileRepository serialization for new fields
    - Update `_to_item()` / `_from_item()` to serialize/deserialize: `notification_preferences` (Map), `language`, `timezone`, `avatar_url`, `bio`, `display_name`, `deleted_at` (ISO 8601 or None)
    - Handle backward compatibility: missing attributes default to safe values
    - _Requirements: 13.1, 13.2, 13.4, 13.5_

  - [ ] 9.2 Implement `list_profiles(page, page_size)` in DynamoDBProfileRepository
    - DynamoDB Scan with `FilterExpression` excluding soft-deleted records
    - Pagination via `ExclusiveStartKey` iteration
    - Returns `(profiles, total_count)`
    - _Requirements: 13.3_

  - [ ]* 9.3 Write integration tests for DynamoDB adapter in `tests/integration/test_dynamodb_repository.py`
    - Test round-trip serialization of UserProfile with all new fields (moto)
    - Test deserialization of legacy items missing new fields uses correct defaults
    - Test `list_profiles` returns correct page and total count
    - Test `list_profiles` excludes soft-deleted profiles
    - _Requirements: 13.1, 13.2, 13.3_

  - [ ]* 9.4 Write property tests for DynamoDB serialization in `tests/property/test_dynamodb_props.py`
    - **Property 21: DynamoDB serialization round-trip**
    - **Validates: Requirements 13.1, 13.4, 13.5**
    - **Property 22: DynamoDB backward compatibility defaults**
    - **Validates: Requirements 13.2**
    - **Property 20: List excludes soft-deleted profiles**
    - **Validates: Requirements 9.7**

- [ ] 10. Infrastructure layer — S3 avatar storage and EventBridge updates
  - [ ] 10.1 Create S3AvatarStorage adapter in `src/infrastructure/adapters/s3_avatar_storage.py`
    - Implement `AvatarStorage` ABC
    - `upload()`: put_object to `ugsys-avatars-{env}` with key `avatars/{user_id}.{extension}`
    - `delete()`: delete_object from bucket
    - _Requirements: 7.1, 7.5, 7.7_

  - [ ]* 10.2 Write integration tests for S3AvatarStorage in `tests/integration/test_s3_avatar_storage.py`
    - Test upload stores file with correct key pattern (moto)
    - Test upload returns correct URL
    - Test delete removes file from bucket
    - _Requirements: 7.1, 7.5, 7.7_

  - [ ]* 10.3 Write property test for avatar key pattern in `tests/property/test_s3_avatar_props.py`
    - **Property 16: Avatar storage key pattern**
    - **Validates: Requirements 7.5**

  - [ ] 10.4 Migrate EventBridgePublisher to implement EventPublisher ABC
    - Implement the domain `EventPublisher` ABC instead of custom `EventPublisherProtocol`
    - Use `ugsys-event-lib` envelope format: `event_id`, `event_version`, `timestamp`, `correlation_id`, `payload`
    - Hardcode source to `"ugsys.user-profile-service"`
    - _Requirements: 3.1, 3.2, 3.3_

  - [ ]* 10.5 Write property test for event envelope format in `tests/property/test_event_publisher_props.py`
    - **Property 8: Event envelope format**
    - **Validates: Requirements 3.2**

  - [ ] 10.6 Update `src/config.py` for event bus name and avatars bucket
    - Change `event_bus_name` default to `"ugsys-platform-bus"` (was `"ugsys-event-bus"`)
    - Add `avatars_bucket_name` field with computed property for `ugsys-avatars-{env}`
    - Add `version` field defaulting to `"0.1.0"`
    - Ensure `profiles_table` property returns `ugsys-profiles-{env}`
    - _Requirements: 3.1, 3.5, 7.1_

- [ ] 11. Checkpoint — Infrastructure layer complete
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 12. Presentation layer — Exception handler and response envelope
  - [ ] 12.1 Create exception handler in `src/presentation/middleware/exception_handler.py`
    - Implement `domain_exception_handler` mapping: `ValidationError→422`, `NotFoundError→404`, `ConflictError→409`, `AuthorizationError→403`, `RepositoryError→500`, `ExternalServiceError→502`
    - Implement `unhandled_exception_handler` returning 500 with generic message, logging full details with `exc_info=True`
    - All error responses wrapped in envelope: `{ "error": { "code": "...", "message": "..." }, "meta": { "request_id": "..." } }`
    - _Requirements: 2.5, 2.6, 2.7_

  - [ ]* 12.2 Write unit tests for exception handler in `tests/unit/presentation/test_exception_handler.py`
    - Test each domain exception type maps to correct HTTP status code
    - Test response body contains `user_message` only (never internal `message`)
    - Test unhandled exception returns 500 with generic message
    - Test error response uses envelope format with `request_id`
    - _Requirements: 2.5, 2.6, 2.7_

  - [ ]* 12.3 Write property test for exception handler in `tests/property/test_exception_handler_props.py`
    - **Property 7: Exception handler maps domain exceptions to HTTP status codes**
    - **Validates: Requirements 2.5, 2.7**

  - [ ] 12.4 Create response envelope utilities in `src/presentation/response_envelope.py`
    - Implement `success_response(data, request_id)` → `{ "data": ..., "meta": { "request_id": ... } }`
    - Implement `list_response(data, total, page, page_size, request_id)` → includes pagination metadata with `total_pages = ceil(total / page_size)`
    - _Requirements: 11.1, 11.2, 11.5_

  - [ ]* 12.5 Write unit tests for response envelope in `tests/unit/presentation/test_response_envelope.py`
    - Test `success_response` wraps data with `meta.request_id`
    - Test `list_response` includes correct pagination metadata and `total_pages` calculation
    - _Requirements: 11.1, 11.2, 11.5_

  - [ ]* 12.6 Write property test for response envelope in `tests/property/test_response_envelope_props.py`
    - **Property 24: Response envelope contains request_id from correlation_id**
    - **Validates: Requirements 11.1, 11.5**

- [ ] 13. Presentation layer — Router updates and new endpoints
  - [ ] 13.1 Update existing profile router endpoints to use envelope wrapping and remove manual try/except
    - Wrap GET /me, GET /{user_id}, PATCH /contact, PATCH /personal responses in `success_response()`
    - Remove manual try/except ValueError/PermissionError blocks (handled by exception_handler)
    - Update profile response DTO to include all new fields: `avatar_url`, `bio`, `display_name`, `language`, `timezone`, `notification_preferences`, `deleted_at`
    - _Requirements: 11.1, 11.3, 11.4_

  - [ ] 13.2 Add avatar endpoints to profiles router
    - `POST /api/v1/profiles/{user_id}/avatar` — Bearer (own or admin), multipart/form-data, returns envelope
    - `DELETE /api/v1/profiles/{user_id}/avatar` — Bearer (own or admin), returns 204
    - _Requirements: 7.1, 7.8, 8.1, 8.3, 8.4_

  - [ ] 13.3 Add preferences and display update endpoints to profiles router
    - `PATCH /api/v1/profiles/{user_id}/preferences` — Bearer (own or admin), returns envelope
    - `PATCH /api/v1/profiles/{user_id}/display` — Bearer (own or admin), returns envelope
    - _Requirements: 12.1, 12.2, 12.3_

  - [ ] 13.4 Add admin endpoints to profiles router
    - `GET /api/v1/profiles` — admin only, paginated, uses `list_response()` with pagination metadata
    - `DELETE /api/v1/profiles/{user_id}` — admin only, returns 204
    - _Requirements: 9.1, 9.2, 9.5, 9.6, 10.1, 10.3, 10.4_

  - [ ]* 13.5 Write unit tests for router endpoints in `tests/unit/presentation/test_profiles_router.py`
    - Test existing endpoints return envelope format
    - Test avatar upload endpoint calls service and returns envelope
    - Test avatar delete endpoint returns 204
    - Test preferences update endpoint calls service and returns envelope
    - Test display update endpoint calls service and returns envelope
    - Test admin list endpoint returns paginated envelope
    - Test admin soft-delete endpoint returns 204
    - Test non-admin gets 403 on admin endpoints
    - _Requirements: 7.1, 8.1, 8.4, 9.1, 9.6, 10.1, 10.3, 11.1, 12.1_

- [ ] 14. Wire everything in main.py — create_app() factory pattern
  - [ ] 14.1 Refactor `src/main.py` to `create_app()` factory pattern
    - Register `domain_exception_handler` and `unhandled_exception_handler` before routers
    - Wire `DynamoDBProfileRepository`, `S3AvatarStorage`, `EventBridgePublisher` via constructor injection
    - Wire `ProfileService` with all three dependencies
    - Disable docs in prod (`docs_url=None` when `environment == "prod"`)
    - Keep `Mangum` handler for Lambda
    - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5_

  - [ ]* 14.2 Write unit tests for main.py wiring in `tests/unit/presentation/test_main.py`
    - Test `create_app()` returns a FastAPI instance with all routers registered
    - Test exception handlers are registered for `DomainError` and `Exception`
    - Test docs disabled when `environment="prod"`
    - Test docs enabled when `environment="dev"`
    - _Requirements: 14.1, 14.3, 14.5_

- [ ] 15. Final checkpoint — Full integration verification
  - Ensure all tests pass, ask the user if questions arise.
  - Verify all 14 requirements are covered by implementation
  - Verify domain exceptions are used everywhere (no raw ValueError/PermissionError from app/domain)
  - Verify all API responses use envelope format
  - Verify event bus name is `ugsys-platform-bus`

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document (Properties 1–24)
- Unit tests validate specific examples and edge cases
- Domain layer tasks (1–3) have zero external dependencies and are instantly testable
- Application layer tasks (5–7) depend only on mockable domain ports
- Infrastructure tasks (9–10) require moto for integration tests
- Presentation tasks (12–13) use FastAPI TestClient with mocked services
