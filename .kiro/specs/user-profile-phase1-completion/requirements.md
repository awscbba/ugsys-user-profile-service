# Requirements Document

## Introduction

Complete all P0, P1, and P2 implementation gaps in the `ugsys-user-profile-service` as defined in the platform contract (`ugsys-documentation/specs/platform-contract.md`, Section 4 and Section 10). The service currently has a working hexagonal architecture with basic CRUD (get, create, update contact/personal, delete), DynamoDB persistence, EventBridge publishing, and all three middleware. This spec closes every remaining gap to reach Phase 1 completion: missing entity fields, domain exception hierarchy, EventBridge consumer handlers, avatar upload/delete, admin endpoints, response envelope standardization, pagination, and event bus name correction.

## Glossary

- **User_Profile_Service**: The `ugsys-user-profile-service` microservice responsible for storing and managing user demographic and contact data
- **UserProfile_Entity**: The core domain object representing a user's profile, stored in DynamoDB table `ugsys-profiles-{env}`
- **Address_Value_Object**: An immutable value object representing a physical address with fields `street`, `city`, `state`, `postal_code`, `country`
- **NotificationPreferences_Value_Object**: An immutable value object representing notification channel preferences with fields `email` (bool), `sms` (bool), `whatsapp` (bool)
- **Profile_Service**: The application-layer service that orchestrates profile use cases (get, create, update, delete, avatar upload/delete, admin list)
- **Profile_Repository**: The outbound port (ABC) defining persistence operations for UserProfile_Entity
- **Event_Publisher**: The infrastructure adapter that publishes domain events to the `ugsys-platform-bus` EventBridge bus using the `ugsys-event-lib` envelope format
- **Event_Consumer**: The Lambda handler that processes inbound EventBridge events from identity-manager (`identity.user.registered`, `identity.user.deactivated`, `identity.auth.password_changed`)
- **Avatar_Storage**: The infrastructure adapter (S3) that handles avatar file upload and deletion in the `ugsys-avatars-{env}` bucket
- **Domain_Exception**: A structured exception hierarchy (`DomainError`, `ConflictError`, `NotFoundError`, `ValidationError`, `AuthorizationError`, `RepositoryError`) that separates internal log messages from user-safe messages
- **Response_Envelope**: The standardized JSON response format `{ "data": ..., "meta": { "request_id": ... } }` for all API responses
- **Exception_Handler**: The presentation-layer middleware that maps domain exceptions to HTTP status codes and returns only user-safe messages

## Requirements

### Requirement 1: UserProfile Entity Field Completion

**User Story:** As a platform developer, I want the UserProfile entity to contain all fields defined in the platform contract Section 4.1, so that downstream services and the admin panel can access complete user profile data.

#### Acceptance Criteria

1. THE UserProfile_Entity SHALL include the fields `notification_preferences` (NotificationPreferences_Value_Object with defaults `email=True`, `sms=False`, `whatsapp=False`), `language` (str, default `"es"`), `timezone` (str, default `"America/La_Paz"`), `avatar_url` (str or None, default None), `bio` (str or None, default None, max 500 characters), and `display_name` (str or None, default None)
2. THE UserProfile_Entity SHALL include a `deleted_at` (datetime or None, default None) field to support soft-delete operations
3. THE UserProfile_Entity SHALL expose a method `update_preferences()` that accepts optional `notification_preferences`, `language`, and `timezone` parameters and updates only the provided fields
4. THE UserProfile_Entity SHALL expose a method `update_display()` that accepts optional `bio` and `display_name` parameters and updates only the provided fields
5. THE UserProfile_Entity SHALL expose a method `soft_delete()` that sets `deleted_at` to the current UTC timestamp
6. IF a `bio` value exceeding 500 characters is provided, THEN THE UserProfile_Entity SHALL truncate the value to 500 characters
7. THE NotificationPreferences_Value_Object SHALL be an immutable dataclass with fields `email` (bool, default True), `sms` (bool, default False), `whatsapp` (bool, default False)

### Requirement 2: Domain Exception Hierarchy

**User Story:** As a developer, I want all application and domain layer code to use a structured domain exception hierarchy, so that error handling is consistent and internal details are never exposed to API callers.

#### Acceptance Criteria

1. THE User_Profile_Service SHALL define a domain exception hierarchy in `src/domain/exceptions.py` containing `DomainError`, `ValidationError`, `NotFoundError`, `ConflictError`, `AuthorizationError`, `RepositoryError`, and `ExternalServiceError`
2. THE Profile_Service SHALL raise `NotFoundError` instead of `ValueError` when a profile is not found
3. THE Profile_Service SHALL raise `ConflictError` instead of `ValueError` when a duplicate profile is detected during creation
4. THE Profile_Service SHALL raise `AuthorizationError` instead of `PermissionError` when an IDOR violation is detected
5. THE User_Profile_Service SHALL register a `domain_exception_handler` in `main.py` that maps each domain exception type to the correct HTTP status code and returns only the `user_message` to the client
6. THE User_Profile_Service SHALL register an `unhandled_exception_handler` that returns HTTP 500 with a generic message and logs the full exception details with `exc_info=True`
7. THE Exception_Handler SHALL map `ValidationError` to HTTP 422, `NotFoundError` to HTTP 404, `ConflictError` to HTTP 409, `AuthorizationError` to HTTP 403, and `RepositoryError` to HTTP 500

### Requirement 3: EventBridge Bus Name Correction and Event Envelope Format

**User Story:** As a platform architect, I want the event bus name and event envelope format to match the platform contract, so that downstream consumers can reliably process events.

#### Acceptance Criteria

1. THE User_Profile_Service config SHALL use `event_bus_name = "ugsys-platform-bus"` instead of `"ugsys-event-bus"`
2. THE Event_Publisher SHALL use the `ugsys-event-lib` envelope format with fields `event_id` (UUID4), `event_version` (str), `timestamp` (ISO 8601 UTC), `correlation_id` (from context), and `payload` (dict)
3. THE Event_Publisher SHALL implement the domain ABC `EventPublisher` defined in `src/domain/repositories/` instead of the current custom `EventPublisherProtocol`
4. WHEN a profile is updated via PATCH /contact or PATCH /personal, THE Event_Publisher SHALL publish a `profile.updated` event with payload containing `user_id` and the list of changed fields
5. THE DynamoDB profiles table name SHALL follow the pattern `ugsys-profiles-{env}` as defined in the platform contract Section 4.2

### Requirement 4: EventBridge Consumer — identity.user.registered

**User Story:** As a platform operator, I want a profile to be automatically created when a new user registers in identity-manager, so that the user has a profile record without manual intervention.

#### Acceptance Criteria

1. WHEN an `identity.user.registered` event is received, THE Event_Consumer SHALL create a new UserProfile_Entity with `user_id`, `email`, and `full_name` extracted from the event payload
2. WHEN an `identity.user.registered` event is received, THE Event_Consumer SHALL set default values for `language` ("es"), `timezone` ("America/La_Paz"), and `notification_preferences` (email=True, sms=False, whatsapp=False)
3. IF a profile already exists for the `user_id` in the event payload, THEN THE Event_Consumer SHALL log a warning and skip creation without raising an error
4. IF the event payload is missing required fields (`user_id`, `email`, `full_name`), THEN THE Event_Consumer SHALL log an error and skip processing without raising an error
5. THE Event_Consumer SHALL be a separate Lambda handler function in `src/infrastructure/messaging/event_consumer.py`

### Requirement 5: EventBridge Consumer — identity.user.deactivated

**User Story:** As a platform operator, I want a profile to be soft-deleted when a user is deactivated in identity-manager, so that deactivated user data is preserved but marked as inactive.

#### Acceptance Criteria

1. WHEN an `identity.user.deactivated` event is received, THE Event_Consumer SHALL call `soft_delete()` on the corresponding UserProfile_Entity and persist the updated state
2. IF no profile exists for the `user_id` in the event payload, THEN THE Event_Consumer SHALL log a warning and skip processing without raising an error
3. THE Event_Consumer SHALL set `deleted_at` to the current UTC timestamp on the UserProfile_Entity

### Requirement 6: EventBridge Consumer — identity.auth.password_changed

**User Story:** As a platform operator, I want the `require_password_change` flag to be cleared on a profile when the user changes their password in identity-manager, so that the profile state stays in sync.

#### Acceptance Criteria

1. WHEN an `identity.auth.password_changed` event is received, THE Event_Consumer SHALL call `clear_password_change_flag()` on the corresponding UserProfile_Entity and persist the updated state
2. IF no profile exists for the `user_id` in the event payload, THEN THE Event_Consumer SHALL log a warning and skip processing without raising an error

### Requirement 7: Avatar Upload Endpoint

**User Story:** As a user, I want to upload a profile avatar image, so that other users and services can display my photo.

#### Acceptance Criteria

1. WHEN a user calls POST `/api/v1/profiles/{user_id}/avatar` with a multipart/form-data file, THE User_Profile_Service SHALL upload the file to the S3 bucket `ugsys-avatars-{env}` and set the `avatar_url` on the UserProfile_Entity
2. THE User_Profile_Service SHALL accept only JPEG, PNG, and WebP file formats for avatar uploads
3. IF the uploaded file exceeds 5 MB, THEN THE Profile_Service SHALL raise a `ValidationError` with user message "File size exceeds the 5 MB limit"
4. IF the uploaded file is not JPEG, PNG, or WebP, THEN THE Profile_Service SHALL raise a `ValidationError` with user message "Only JPEG, PNG, and WebP formats are accepted"
5. THE Avatar_Storage SHALL store files with the key pattern `avatars/{user_id}.{extension}` in the S3 bucket
6. WHEN an avatar is uploaded, THE Event_Publisher SHALL publish a `profile.avatar_updated` event with payload containing `user_id` and `avatar_url`
7. WHEN a user already has an avatar, THE Avatar_Storage SHALL overwrite the existing file
8. THE avatar upload endpoint SHALL require Bearer authentication and enforce IDOR checks (own profile or admin)

### Requirement 8: Avatar Delete Endpoint

**User Story:** As a user, I want to remove my profile avatar, so that I can revert to a default or no-avatar state.

#### Acceptance Criteria

1. WHEN a user calls DELETE `/api/v1/profiles/{user_id}/avatar`, THE User_Profile_Service SHALL delete the avatar file from S3 and set `avatar_url` to None on the UserProfile_Entity
2. IF no avatar exists for the user, THEN THE Profile_Service SHALL set `avatar_url` to None without raising an error
3. THE avatar delete endpoint SHALL require Bearer authentication and enforce IDOR checks (own profile or admin)
4. THE User_Profile_Service SHALL return HTTP 204 on successful avatar deletion

### Requirement 9: Admin List Profiles Endpoint

**User Story:** As an admin, I want to list all user profiles with pagination, so that I can browse and manage user data efficiently.

#### Acceptance Criteria

1. WHEN an admin calls GET `/api/v1/profiles`, THE User_Profile_Service SHALL return a paginated list of UserProfile_Entity records
2. THE User_Profile_Service SHALL accept query parameters `page` (default 1) and `page_size` (default 20, max 100)
3. IF `page_size` exceeds 100, THEN THE User_Profile_Service SHALL cap the value at 100 without raising an error
4. THE Profile_Repository SHALL expose a `list_profiles(page, page_size)` method that returns a tuple of (profiles list, total count)
5. THE User_Profile_Service SHALL include pagination metadata in the response envelope: `total`, `page`, `page_size`, `total_pages`
6. IF a non-admin user calls GET `/api/v1/profiles`, THEN THE User_Profile_Service SHALL return HTTP 403
7. THE list endpoint SHALL exclude soft-deleted profiles (where `deleted_at` is not None) from results

### Requirement 10: Admin Soft-Delete Profile Endpoint

**User Story:** As an admin, I want to soft-delete a user profile, so that I can deactivate profiles while preserving the data for audit purposes.

#### Acceptance Criteria

1. WHEN an admin calls DELETE `/api/v1/profiles/{user_id}`, THE Profile_Service SHALL call `soft_delete()` on the UserProfile_Entity and persist the updated state
2. IF the target profile does not exist, THEN THE Profile_Service SHALL raise a `NotFoundError`
3. IF a non-admin user calls DELETE `/api/v1/profiles/{user_id}`, THEN THE User_Profile_Service SHALL return HTTP 403
4. THE User_Profile_Service SHALL return HTTP 204 on successful soft-delete
5. WHEN a profile is soft-deleted by an admin, THE Event_Publisher SHALL publish a `profile.deleted` event with payload containing `user_id`

### Requirement 11: Response Envelope Standardization

**User Story:** As an API consumer, I want all responses to follow a consistent envelope format, so that client-side parsing logic is uniform across all endpoints.

#### Acceptance Criteria

1. THE User_Profile_Service SHALL wrap all successful single-resource responses in `{ "data": { ... }, "meta": { "request_id": "<correlation_id>" } }`
2. THE User_Profile_Service SHALL wrap all successful list responses in `{ "data": [ ... ], "meta": { "request_id": "...", "total": N, "page": N, "page_size": N, "total_pages": N } }`
3. THE User_Profile_Service SHALL wrap all error responses in `{ "error": { "code": "...", "message": "..." }, "meta": { "request_id": "..." } }`
4. THE profile response DTO SHALL include all new fields: `avatar_url`, `bio`, `display_name`, `language`, `timezone`, `notification_preferences`, `deleted_at`
5. THE User_Profile_Service SHALL return the `correlation_id` from the CorrelationIdMiddleware as the `request_id` in the `meta` object

### Requirement 12: Profile Update Preferences and Display Endpoints

**User Story:** As a user, I want to update my notification preferences, language, timezone, bio, and display name, so that my profile reflects my current preferences.

#### Acceptance Criteria

1. WHEN a user calls PATCH `/api/v1/profiles/{user_id}/preferences`, THE Profile_Service SHALL update `notification_preferences`, `language`, and `timezone` on the UserProfile_Entity using only the provided fields
2. WHEN a user calls PATCH `/api/v1/profiles/{user_id}/display`, THE Profile_Service SHALL update `bio` and `display_name` on the UserProfile_Entity using only the provided fields
3. THE preferences and display update endpoints SHALL require Bearer authentication and enforce IDOR checks (own profile or admin)
4. WHEN preferences or display fields are updated, THE Event_Publisher SHALL publish a `profile.updated` event with payload containing `user_id` and the list of changed fields
5. IF a `bio` value exceeding 500 characters is provided via the API, THEN THE Profile_Service SHALL raise a `ValidationError` with user message "Bio must not exceed 500 characters"

### Requirement 13: DynamoDB Persistence for New Fields

**User Story:** As a developer, I want the DynamoDB adapter to persist and retrieve all new UserProfile entity fields, so that profile data survives across Lambda invocations.

#### Acceptance Criteria

1. THE DynamoDB adapter SHALL serialize and deserialize all new UserProfile_Entity fields: `notification_preferences`, `language`, `timezone`, `avatar_url`, `bio`, `display_name`, `deleted_at`
2. THE DynamoDB adapter SHALL handle missing attributes gracefully by using default values for new fields when reading records created before the schema update
3. THE DynamoDB adapter SHALL implement the `list_profiles(page, page_size)` method using DynamoDB Scan with pagination and a filter expression excluding soft-deleted records
4. THE DynamoDB adapter SHALL serialize `notification_preferences` as a DynamoDB Map attribute with keys `email`, `sms`, `whatsapp`
5. THE DynamoDB adapter SHALL serialize `deleted_at` as an ISO 8601 string or None

### Requirement 14: Application Factory Pattern Alignment

**User Story:** As a developer, I want `main.py` to follow the `create_app()` factory pattern, so that the composition root is consistent with all other ugsys services.

#### Acceptance Criteria

1. THE User_Profile_Service `main.py` SHALL use a `create_app()` factory function as the single composition root
2. THE `create_app()` function SHALL register exception handlers before routers
3. THE `create_app()` function SHALL disable docs in production (`docs_url=None` when `environment == "prod"`)
4. THE `create_app()` function SHALL wire the Profile_Service dependency using constructor injection, not global singletons
5. WHEN the environment is not production, THE `create_app()` function SHALL expose Swagger docs at `/docs`
