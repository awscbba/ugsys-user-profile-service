# Requirements Document

## Introduction

The `profile-frontend` is a React 19 single-page application (SPA) served at
`https://profile.apps.cloud.org.bo`. It is the UI that users land on when they
click "Mi Perfil" from any microservice's `UserMenu`. The SPA is fully
authenticated — every route requires a valid session. It communicates exclusively
with the existing `ugsys-user-profile-service` backend API (same origin) and with
the `ugsys-identity-manager` for session management.

The tech stack mirrors `ugsys-projects-registry/web`: React 19 + TypeScript,
Vite, Tailwind CSS v4, react-router-dom v7, nanostores + @nanostores/react,
`@ugsys/ui-lib` shared components, Vitest + React Testing Library, and pnpm.

---

## Glossary

- **SPA**: The profile-frontend single-page application served at `profile.apps.cloud.org.bo`.
- **Auth_Store**: The nanostores atom that holds the in-memory access token and authenticated user identity.
- **Profile_Store**: The nanostores atom that holds the fetched `ProfileResponse` and loading/error state.
- **Profile_API**: The HTTP client module that wraps all calls to `/api/v1/profiles/*` endpoints.
- **Auth_API**: The HTTP client module that wraps calls to `/api/v1/auth/*` on the identity-manager.
- **ProfileResponse**: The JSON shape returned by `GET /api/v1/profiles/me` (defined in the Introduction).
- **Toast_Service**: The module responsible for displaying non-blocking error and success notifications.
- **Avatar_Uploader**: The UI component and logic responsible for avatar file selection, validation, preview, and upload.
- **Edit_Section**: A profile sub-section (personal / contact / display / preferences) that supports inline editing with optimistic update and revert-on-error behaviour.
- **UserMenu**: The shared component from `@ugsys/ui-lib` rendered in the Navbar.
- **Identity_Manager**: The service at `https://auth.apps.cloud.org.bo` that owns authentication.

---

## Requirements

### Requirement 1: Session Restoration on Startup

**User Story:** As a user, I want my session to be automatically restored when I
open the profile page, so that I do not have to log in again if my refresh token
cookie is still valid.

#### Acceptance Criteria

1. WHEN the SPA initialises, THE Auth_Store SHALL call `POST /api/v1/auth/refresh`
   on the Identity_Manager with `credentials: 'include'` before rendering any
   protected content.
2. WHEN the refresh call returns HTTP 200, THE Auth_Store SHALL store the returned
   access token in memory and mark the session as authenticated.
3. WHEN the refresh call returns HTTP 401, THE SPA SHALL redirect the browser to
   `https://auth.apps.cloud.org.bo/login?redirect=https://profile.apps.cloud.org.bo`.
4. WHILE the refresh call is in flight, THE SPA SHALL render a full-page loading
   indicator and SHALL NOT render any profile content.
5. IF the refresh call returns any HTTP status other than 200 or 401, THEN THE
   SPA SHALL redirect to the Identity_Manager login page as if a 401 was received.

---

### Requirement 2: Profile Display

**User Story:** As an authenticated user, I want to see all my profile information
on a single page, so that I can review my personal, contact, display, and
preference data at a glance.

#### Acceptance Criteria

1. WHEN the session is authenticated, THE Profile_API SHALL call
   `GET /api/v1/profiles/me` with `Authorization: Bearer <access_token>`.
2. WHEN `GET /api/v1/profiles/me` returns HTTP 200, THE Profile_Store SHALL
   populate with the returned `ProfileResponse` and the SPA SHALL render all
   fields defined in the ProfileResponse shape.
3. WHEN `avatar_url` is non-null, THE SPA SHALL render the avatar image from
   that URL; WHEN `avatar_url` is null, THE SPA SHALL render a default avatar
   placeholder.
4. WHEN `display_name` is non-null, THE SPA SHALL render `display_name` as the
   primary name; WHEN `display_name` is null, THE SPA SHALL render `full_name`
   as the primary name.
5. WHEN `GET /api/v1/profiles/me` returns HTTP 401, THE SPA SHALL redirect to
   the Identity_Manager login page.
6. IF `GET /api/v1/profiles/me` returns any non-200, non-401 status, THEN THE
   Toast_Service SHALL display an error notification and THE SPA SHALL not render
   stale data from a previous load.

---

### Requirement 3: Edit Personal Information

**User Story:** As an authenticated user, I want to edit my full name and date of
birth inline, so that I can keep my personal information up to date without
navigating to a separate page.

#### Acceptance Criteria

1. WHEN the user activates the personal info Edit_Section, THE SPA SHALL render
   editable fields for `full_name` and `date_of_birth`.
2. WHEN the user submits the personal info Edit_Section, THE Profile_API SHALL
   call `PATCH /api/v1/profiles/{user_id}/personal` with the updated values and
   `Authorization: Bearer <access_token>`.
3. WHEN the PATCH call is in flight, THE Profile_Store SHALL immediately reflect
   the submitted values (optimistic update) and THE SPA SHALL disable the submit
   control.
4. WHEN the PATCH call returns HTTP 200, THE Profile_Store SHALL retain the
   optimistically applied values and THE Edit_Section SHALL return to read mode.
5. IF the PATCH call returns a non-200 status, THEN THE Profile_Store SHALL
   revert to the values held before the edit was submitted and THE Toast_Service
   SHALL display an error notification.
6. THE SPA SHALL validate that `full_name` is non-empty before submitting.

---

### Requirement 4: Edit Contact Information

**User Story:** As an authenticated user, I want to edit my phone number and
address inline, so that I can keep my contact details current.

#### Acceptance Criteria

1. WHEN the user activates the contact info Edit_Section, THE SPA SHALL render
   editable fields for `phone`, `street`, `city`, `state`, `postal_code`, and
   `country`.
2. WHEN the user submits the contact info Edit_Section, THE Profile_API SHALL
   call `PATCH /api/v1/profiles/{user_id}/contact` with the updated values and
   `Authorization: Bearer <access_token>`.
3. WHEN the PATCH call is in flight, THE Profile_Store SHALL immediately reflect
   the submitted values (optimistic update) and THE SPA SHALL disable the submit
   control.
4. WHEN the PATCH call returns HTTP 200, THE Profile_Store SHALL retain the
   optimistically applied values and THE Edit_Section SHALL return to read mode.
5. IF the PATCH call returns a non-200 status, THEN THE Profile_Store SHALL
   revert to the pre-edit values and THE Toast_Service SHALL display an error
   notification.

---

### Requirement 5: Edit Display Information

**User Story:** As an authenticated user, I want to edit my bio and display name
inline, so that I can control how I appear to other users.

#### Acceptance Criteria

1. WHEN the user activates the display info Edit_Section, THE SPA SHALL render
   editable fields for `bio` and `display_name`.
2. WHILE the user is editing `bio`, THE SPA SHALL display a character counter
   showing the number of characters remaining out of the 500-character maximum.
3. THE SPA SHALL prevent submission of a `bio` value that exceeds 500 characters.
4. WHEN the user submits the display info Edit_Section, THE Profile_API SHALL
   call `PATCH /api/v1/profiles/{user_id}/display` with the updated values and
   `Authorization: Bearer <access_token>`.
5. WHEN the PATCH call is in flight, THE Profile_Store SHALL immediately reflect
   the submitted values (optimistic update) and THE SPA SHALL disable the submit
   control.
6. WHEN the PATCH call returns HTTP 200, THE Profile_Store SHALL retain the
   optimistically applied values and THE Edit_Section SHALL return to read mode.
7. IF the PATCH call returns a non-200 status, THEN THE Profile_Store SHALL
   revert to the pre-edit values and THE Toast_Service SHALL display an error
   notification.

---

### Requirement 6: Edit Preferences

**User Story:** As an authenticated user, I want to manage my notification
channels, language, and timezone preferences, so that I receive communications
through the channels and in the locale I prefer.

#### Acceptance Criteria

1. WHEN the user activates the preferences Edit_Section, THE SPA SHALL render
   toggle controls for `notification_preferences.email`,
   `notification_preferences.sms`, and `notification_preferences.whatsapp`, a
   language selector populated with supported ISO 639-1 codes, and a timezone
   selector populated with IANA timezone identifiers.
2. WHEN the user submits the preferences Edit_Section, THE Profile_API SHALL
   call `PATCH /api/v1/profiles/{user_id}/preferences` with the updated values
   and `Authorization: Bearer <access_token>`.
3. WHEN the PATCH call is in flight, THE Profile_Store SHALL immediately reflect
   the submitted values (optimistic update) and THE SPA SHALL disable the submit
   control.
4. WHEN the PATCH call returns HTTP 200, THE Profile_Store SHALL retain the
   optimistically applied values and THE Edit_Section SHALL return to read mode.
5. IF the PATCH call returns a non-200 status, THEN THE Profile_Store SHALL
   revert to the pre-edit values and THE Toast_Service SHALL display an error
   notification.

---

### Requirement 7: Avatar Upload and Deletion

**User Story:** As an authenticated user, I want to upload or delete my avatar
image, so that I can personalise my profile picture.

#### Acceptance Criteria

1. WHEN the user clicks the avatar area, THE Avatar_Uploader SHALL open a file
   picker restricted to JPEG, PNG, and WebP MIME types.
2. IF the selected file exceeds 5 MB, THEN THE Avatar_Uploader SHALL reject the
   file, SHALL NOT send any request to the server, and THE Toast_Service SHALL
   display an error notification stating the size limit.
3. IF the selected file has a MIME type other than `image/jpeg`, `image/png`, or
   `image/webp`, THEN THE Avatar_Uploader SHALL reject the file, SHALL NOT send
   any request to the server, and THE Toast_Service SHALL display an error
   notification stating the accepted types.
4. WHEN a valid file is selected, THE Avatar_Uploader SHALL display a preview of
   the selected image before the user confirms the upload.
5. WHEN the user confirms the upload, THE Profile_API SHALL call
   `POST /api/v1/profiles/{user_id}/avatar` with the file as `multipart/form-data`
   and `Authorization: Bearer <access_token>`.
6. WHEN the upload call returns HTTP 200, THE Profile_Store SHALL update
   `avatar_url` with the value returned by the server.
7. IF the upload call returns a non-200 status, THEN THE Profile_Store SHALL
   retain the previous `avatar_url` and THE Toast_Service SHALL display an error
   notification.
8. WHEN the user chooses to delete the avatar, THE Profile_API SHALL call
   `DELETE /api/v1/profiles/{user_id}/avatar` with `Authorization: Bearer
   <access_token>`.
9. WHEN the delete call returns HTTP 200, THE Profile_Store SHALL set `avatar_url`
   to null and THE SPA SHALL render the default avatar placeholder.
10. IF the delete call returns a non-200 status, THEN THE Profile_Store SHALL
    retain the previous `avatar_url` and THE Toast_Service SHALL display an error
    notification.

---

### Requirement 8: Shared Layout

**User Story:** As a user, I want the profile page to use the same navigation
shell as the rest of the platform, so that I can navigate between services
consistently.

#### Acceptance Criteria

1. THE SPA SHALL render the `Navbar` and `Footer` components from `@ugsys/ui-lib`
   on every page.
2. THE SPA SHALL render the `UserMenu` component from `@ugsys/ui-lib` inside the
   Navbar with `profileHref` set to `https://profile.apps.cloud.org.bo` and
   `adminPanelUrl` set to `https://admin.apps.cloud.org.bo`.
3. WHEN the user triggers logout via the UserMenu, THE Auth_API SHALL call
   `POST /api/v1/auth/logout` on the Identity_Manager with `credentials: 'include'`.
4. WHEN the logout call completes (regardless of status), THE Auth_Store SHALL
   clear the in-memory access token and THE SPA SHALL redirect to
   `https://auth.apps.cloud.org.bo/login`.

---

### Requirement 9: Error Handling and Notifications

**User Story:** As a user, I want to be informed of errors through clear
notifications, so that I understand when an action has failed without seeing
technical details.

#### Acceptance Criteria

1. WHEN any Profile_API call returns a non-200 status, THE Toast_Service SHALL
   display a human-readable error notification.
2. THE Toast_Service SHALL never include HTTP status codes, stack traces, server
   error messages, or internal field names in the notification text shown to the
   user.
3. WHEN a notification is displayed, THE Toast_Service SHALL automatically dismiss
   it after 5 seconds unless the user dismisses it earlier.
4. THE SPA SHALL display at most 3 simultaneous toast notifications; additional
   notifications SHALL queue and appear as earlier ones are dismissed.

---

### Requirement 10: Correctness Properties

**User Story:** As a developer, I want the SPA to satisfy verifiable correctness
properties, so that automated tests can confirm the system behaves correctly
across all states.

#### Acceptance Criteria

1. FOR ALL authenticated users, the values rendered on the profile page SHALL
   equal the corresponding fields in the `ProfileResponse` returned by
   `GET /api/v1/profiles/me` (display fidelity property).
2. FOR ALL Edit_Section submissions that receive HTTP 200, the value displayed
   after the response SHALL equal the value that was submitted (successful-update
   consistency property).
3. FOR ALL Edit_Section submissions that receive a non-200 response, the value
   displayed after the response SHALL equal the value that was displayed before
   the edit was activated (revert-on-error property).
4. FOR ALL unauthenticated users (refresh returns 401 or no cookie present), THE
   SPA SHALL redirect to the Identity_Manager login URL and SHALL NOT render any
   profile content (authentication gate property).
5. FOR ALL avatar file selections where the file size exceeds 5 MB or the MIME
   type is not `image/jpeg`, `image/png`, or `image/webp`, THE Avatar_Uploader
   SHALL reject the file client-side and SHALL NOT call
   `POST /api/v1/profiles/{user_id}/avatar` (client-side validation property).
