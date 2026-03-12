# Implementation Plan: profile-frontend

## Overview

React 19 SPA at `web/` inside `ugsys-user-profile-service`. Fully authenticated, cookie-based
session, single profile page with four inline-edit sections and avatar management. Mirrors the
`ugsys-projects-registry/web` stack exactly.

## Tasks

- [x] 1. Project scaffold
  - Create `web/` directory with `package.json` (React 19, TypeScript, Vite, Tailwind CSS v4,
    react-router-dom v7, nanostores, @nanostores/react, @ugsys/ui-lib, fast-check as devDep)
  - Create `web/index.html` with root `<div id="root">` and script entry
  - Create `web/vite.config.ts` with `@vitejs/plugin-react`, path alias `@/` → `src/`,
    `server.proxy` for `/api` → profile-service and `/auth-api` → identity-manager in dev
  - Create `web/tsconfig.json` with strict mode, `paths` matching vite alias
  - Create `web/vitest.config.ts` with jsdom environment, setup file, coverage thresholds
    (80% branches/lines/functions/statements)
  - Create `web/src/index.css` importing Tailwind CSS v4 (`@import "tailwindcss"`)
  - Create `web/src/main.tsx` as a stub that exports `renderApp` (wired in task 13)
  - _Requirements: 8.1_

- [x] 2. Types and data models
  - Create `web/src/types/auth.ts` — `AuthUser { sub, email, roles }`
  - Create `web/src/types/profile.ts` — `AddressResponse`, `NotificationPreferencesResponse`,
    `ProfileResponse`, `UpdatePersonalRequest`, `UpdateContactRequest`, `UpdateDisplayRequest`,
    `UpdatePreferencesRequest`
  - _Requirements: 2.2, 3.1, 4.1, 5.1, 6.1_

- [x] 3. Toast utility
  - Create `web/src/utils/toast.ts` — `Toast` interface, `$toasts` atom, `addToast` (caps at 3,
    schedules `setTimeout` 5 000 ms auto-dismiss), `dismissToast`
  - [ ]* 3.1 Write property test for Toast Maximum Simultaneous Count
    - **Property 11: Toast Maximum Simultaneous Count**
    - **Validates: Requirements 9.4**
    - Tag: `// Feature: profile-frontend, Property 11`
    - `fc.array(fc.string({ minLength: 1 }), { minLength: 4, maxLength: 20 })` — after N calls
      `$toasts.get().length` must be ≤ 3
  - [ ]* 3.2 Write property test for Toast Auto-Dismiss
    - **Property 12: Toast Auto-Dismiss**
    - **Validates: Requirements 9.3**
    - Tag: `// Feature: profile-frontend, Property 12`
    - `fc.string({ minLength: 1 })` — after `vi.advanceTimersByTime(5_000)` toast is gone
  - [ ]* 3.3 Write unit tests for toast utility
    - `addToast` adds a toast; `dismissToast` removes it; cap enforced; auto-dismiss timer fires
    - _Requirements: 9.3, 9.4_

- [x] 4. Auth store and auth service
  - Create `web/src/services/authService.ts` — `authService.refresh()` and `authService.logout()`
    using raw `fetch` with `credentials: 'include'` against `VITE_AUTH_API_URL`
  - Create `web/src/stores/authStore.ts` — `_accessToken` closure, `getAccessToken`,
    `setAccessToken`, `clearAccessToken`, `$user`, `$isInitializing`, `$isAuthenticated`,
    `initializeAuth()` (calls `authService.refresh()`, on 200 sets token + `$user`, on non-200
    redirects to login), `logout()` (clears token, calls `authService.logout()`, redirects)
  - [ ]* 4.1 Write property test for Non-200 Refresh Redirects to Login
    - **Property 1: Non-200 Refresh Redirects to Login**
    - **Validates: Requirements 1.3, 1.5**
    - Tag: `// Feature: profile-frontend, Property 1`
    - `fc.integer({ min: 201, max: 599 }).filter(s => s !== 200)` — `initializeAuth()` must set
      `window.location.href` to login URL and `$user.get()` must remain null
  - [ ]* 4.2 Write unit tests for authStore
    - 200 path: token stored, `$user` set, `$isInitializing` false
    - 401 path: redirect to login, `$user` null
    - `logout()`: token cleared, redirect fires
    - `$isAuthenticated` computed: true when `$user` non-null
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 8.3, 8.4_

- [x] 5. HTTP client
  - Create `web/src/services/httpClient.ts` — `apiFetch` wrapper with `Authorization: Bearer`
    header from `getAccessToken()`, 15 000 ms `AbortController` timeout, 401 interceptor that
    calls `authService.refresh()` once (cookie-based), retries original request on success,
    redirects to login on second 401; extracts `user_message` from ugsys error envelope,
    falls back to `"No se pudo completar la solicitud"`
  - _Requirements: 1.1, 2.1, 3.2, 4.2, 5.4, 6.2, 7.5, 7.8_

- [x] 6. Profile store and profile service
  - Create `web/src/services/profileService.ts` — `getMe`, `updatePersonal`, `updateContact`,
    `updateDisplay`, `updatePreferences`, `uploadAvatar` (FormData, no Content-Type header),
    `deleteAvatar`; all calls via `apiFetch`
  - Create `web/src/stores/profileStore.ts` — `$profile`, `$profileLoading`, `$profileError`,
    `loadProfile()` (calls `profileService.getMe()`, sets store, toasts on non-200 non-401 error)
  - [ ]* 6.1 Write property test for Display Fidelity
    - **Property 2: Display Fidelity**
    - **Validates: Requirements 2.2, 10.1**
    - Tag: `// Feature: profile-frontend, Property 2`
    - `arbitraryProfileResponse()` — after `$profile.set(profile)` every scalar field value
      appears in the rendered `ProfilePage` output
  - [ ]* 6.2 Write unit tests for profileStore
    - `loadProfile` success: `$profile` populated, `$profileLoading` false
    - `loadProfile` 401: redirect fires
    - `loadProfile` non-200 non-401: toast added, `$profile` stays null
    - _Requirements: 2.1, 2.2, 2.5, 2.6_

- [x] 7. useEditSection hook
  - Create `web/src/hooks/useEditSection.ts` — `UseEditSectionOptions<T>`, `UseEditSectionResult<T>`;
    `startEdit` copies `currentValue` to `draft`; `submitEdit` runs `validate`, snapshots
    `$profile`, applies optimistic update, calls `onSave`, on success sets `$profile` to
    response and closes edit, on error reverts snapshot and calls `addToast`; `cancelEdit`
    discards draft; `isSaving` guards submit
  - [ ]* 7.1 Write property test for Optimistic Update Applied Immediately
    - **Property 3: Optimistic Update Applied Immediately**
    - **Validates: Requirements 3.3, 4.3, 5.5, 6.3**
    - Tag: `// Feature: profile-frontend, Property 3`
    - `arbitraryProfileResponse()` + `arbitraryPersonalDraft()` — `$profile` reflects draft
      synchronously before the mocked PATCH resolves
  - [ ]* 7.2 Write property test for Successful-Update Consistency
    - **Property 4: Successful-Update Consistency**
    - **Validates: Requirements 3.4, 4.4, 5.6, 6.4, 10.2**
    - Tag: `// Feature: profile-frontend, Property 4`
    - `arbitraryProfileResponse()` + `arbitraryPersonalDraft()` — after 200 response
      `$profile.get()` equals the submitted draft merged into the response
  - [ ]* 7.3 Write property test for Revert-on-Error
    - **Property 5: Revert-on-Error**
    - **Validates: Requirements 3.5, 4.5, 5.7, 6.5, 10.3**
    - Tag: `// Feature: profile-frontend, Property 5`
    - `arbitraryProfileResponse()` + `arbitraryPersonalDraft()` + `fc.integer({ min: 400, max: 599 })`
      — after non-200 PATCH `$profile.get()` equals the pre-edit snapshot
  - [ ]* 7.4 Write unit tests for useEditSection
    - Validation error blocks API call; `isSaving` true while in-flight; `cancelEdit` discards draft
    - _Requirements: 3.3, 3.4, 3.5, 3.6_

- [x] 8. Checkpoint — stores, services, and hook
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 9. Layout components
  - Create `web/src/components/layout/Layout.tsx` — renders `<Navbar>` + `<UserMenu>` from
    `@ugsys/ui-lib` with `profileHref`, `adminPanelUrl`, `user={$user}`, `onLogout={logout}`,
    `renderLink`; wraps `<Outlet />` in `<AuthGate>`; renders `<Footer>` and `<ToastContainer>`
  - Create `web/src/components/layout/AuthGate.tsx` — reads `$isInitializing` and
    `$isAuthenticated`; renders full-page spinner while initializing; renders nothing (safety
    net) when not authenticated; renders `children` when authenticated
  - [ ]* 9.1 Write property test for Authentication Gate
    - **Property 13: Authentication Gate**
    - **Validates: Requirements 1.3, 1.5, 10.4**
    - Tag: `// Feature: profile-frontend, Property 13`
    - When `$isAuthenticated` is false and `$isInitializing` is false, `AuthGate` renders no
      children and `window.location.href` points to the login URL
  - [ ]* 9.2 Write unit tests for AuthGate
    - Spinner rendered while `$isInitializing` true; children rendered when authenticated;
      nothing rendered when not authenticated and not initializing
    - _Requirements: 1.4, 8.1_

- [ ] 10. Profile sections
  - Create `web/src/components/profile/PersonalSection.tsx` — read/edit toggle via
    `useEditSection`; fields `full_name` (text) and `date_of_birth` (date); validates
    `full_name.trim().length > 0`; calls `profileService.updatePersonal`
  - Create `web/src/components/profile/ContactSection.tsx` — read/edit toggle via
    `useEditSection`; fields `phone`, `street`, `city`, `state`, `postal_code`, `country`;
    calls `profileService.updateContact`
  - Create `web/src/components/profile/DisplaySection.tsx` — read/edit toggle via
    `useEditSection`; fields `bio` (textarea with `data-testid="bio-counter"` showing
    `500 - bio.length`) and `display_name`; validates `bio.length <= 500`; calls
    `profileService.updateDisplay`
  - Create `web/src/components/profile/PreferencesSection.tsx` — read/edit toggle via
    `useEditSection`; checkbox toggles for `email`, `sms`, `whatsapp`; `<select>` for
    language (ISO 639-1) and timezone (IANA); calls `profileService.updatePreferences`
  - [ ]* 10.1 Write property test for Bio Character Counter Accuracy
    - **Property 6: Bio Character Counter Accuracy**
    - **Validates: Requirements 5.2**
    - Tag: `// Feature: profile-frontend, Property 6`
    - `fc.string({ maxLength: 500 })` — `data-testid="bio-counter"` text equals `500 - bio.length`
  - [ ]* 10.2 Write property test for Bio Length Validation
    - **Property 7: Bio Length Validation**
    - **Validates: Requirements 5.3**
    - Tag: `// Feature: profile-frontend, Property 7`
    - `fc.string({ minLength: 501 })` — submit button disabled, no fetch call made
  - [ ]* 10.3 Write property test for full_name Non-Empty Validation
    - **Property 8: full_name Non-Empty Validation**
    - **Validates: Requirements 3.6**
    - Tag: `// Feature: profile-frontend, Property 8`
    - `fc.stringMatching(/^\s*$/)` — submit button disabled, no fetch call made
  - [ ]* 10.4 Write unit tests for PersonalSection
    - Read mode renders `full_name` and `date_of_birth`; edit mode shows inputs; empty name
      blocks submit
    - _Requirements: 3.1, 3.2, 3.6_
  - [ ]* 10.5 Write unit tests for DisplaySection
    - Counter visible in edit mode; bio > 500 chars disables submit
    - _Requirements: 5.1, 5.2, 5.3_

- [ ] 11. Avatar uploader
  - Create `web/src/components/profile/AvatarUploader.tsx` — hidden `<input type="file">`
    restricted to `image/jpeg,image/png,image/webp`; `onChange` rejects files > 5 242 880 bytes
    or invalid MIME with `addToast`; valid file sets `preview` via `URL.createObjectURL`;
    Confirm calls `profileService.uploadAvatar`, updates `$profile.avatar_url` on 200;
    Cancel clears preview; Delete button calls `profileService.deleteAvatar`, sets
    `avatar_url` to null on 200; renders default placeholder when `avatarUrl` is null
  - [ ]* 11.1 Write property test for Invalid Avatar File Rejected Client-Side
    - **Property 9: Invalid Avatar File Rejected Client-Side**
    - **Validates: Requirements 7.2, 7.3, 10.5**
    - Tag: `// Feature: profile-frontend, Property 9`
    - `fc.oneof(arbitraryOversizedFile(), arbitraryInvalidMimeFile())` — no fetch call made,
      `$toasts.get().length > 0`
  - [ ]* 11.2 Write unit tests for AvatarUploader
    - Valid file shows preview and Confirm/Cancel buttons; size rejection toasts; MIME rejection
      toasts; Confirm triggers upload; Delete triggers delete call; 200 updates store;
      non-200 retains previous `avatar_url`
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8, 7.9, 7.10_

- [ ] 12. Toast component
  - Create `web/src/components/ui/Toast.tsx` — `ToastContainer` reads `$toasts` via `useStore`,
    renders fixed bottom-right stack of up to 3 `Toast` items; each item has dismiss button
    that calls `dismissToast`; applies fade-out CSS transition on removal
  - [ ]* 12.1 Write property test for Toast Safety
    - **Property 10: Toast Safety**
    - **Validates: Requirements 9.1, 9.2**
    - Tag: `// Feature: profile-frontend, Property 10`
    - `fc.integer({ min: 400, max: 599 })` as mock response status — rendered toast text must
      not match `/\d{3}/` (no status codes), must not contain stack trace markers or field names
  - [ ]* 12.2 Write unit tests for Toast component
    - `ToastContainer` renders toasts from `$toasts`; dismiss button calls `dismissToast`;
      renders at most 3 items
    - _Requirements: 9.1, 9.2, 9.3, 9.4_

- [ ] 13. ProfilePage assembly
  - Create `web/src/pages/ProfilePage.tsx` — calls `loadProfile()` on mount via `useEffect`;
    reads `$profile` and `$profileLoading`; renders skeleton while loading; renders
    `AvatarUploader` then `PersonalSection`, `ContactSection`, `DisplaySection`,
    `PreferencesSection`; renders `display_name` as primary name when non-null, else
    `full_name`; renders default avatar placeholder when `avatar_url` is null
  - [ ]* 13.1 Write unit tests for ProfilePage
    - Skeleton shown while loading; all section components rendered after load; display_name
      takes precedence over full_name; null avatar_url shows placeholder
    - _Requirements: 2.2, 2.3, 2.4_

- [ ] 14. Router and main.tsx wiring
  - Create `web/src/app/router.tsx` — `createBrowserRouter` with `Layout` as root element and
    `ProfilePage` at path `/`
  - Complete `web/src/main.tsx` — `await initializeAuth()` before `ReactDOM.createRoot(...).render(...)`;
    wraps app in `<RouterProvider router={router} />`
  - _Requirements: 1.1, 1.4, 8.1, 8.2_

- [ ] 15. Final checkpoint — all tests pass
  - Ensure all tests pass, ask the user if questions arise.
  - Run `pnpm --filter web test --run` and confirm 80%+ coverage gate passes.

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP
- All 13 correctness properties must have corresponding property-based tests using fast-check
  with `{ numRuns: 100 }` and the tag `// Feature: profile-frontend, Property N`
- `authService` uses raw `fetch` (not `httpClient`) to avoid circular dependency
- `uploadAvatar` must omit `Content-Type` so the browser sets the multipart boundary
- Toast messages must be in Spanish and must never expose HTTP status codes, field names,
  or server error text
- `$isInitializing` starts as `true`; `AuthGate` blocks all profile content until it resolves
