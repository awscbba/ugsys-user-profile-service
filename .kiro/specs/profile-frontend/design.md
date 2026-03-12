# Design Document — profile-frontend

## Overview

The `profile-frontend` is a React 19 SPA served at `https://profile.apps.cloud.org.bo`.
It is the user profile management UI for the `ugsys-user-profile-service`. Users land here
when they click "Mi Perfil" from any microservice's `UserMenu`.

The SPA is fully authenticated — every render requires a valid session. On startup it
restores the session by calling `POST /api/v1/auth/refresh` on the Identity Manager with
`credentials: 'include'` (cookie-based, per the cross-service-session bugfix). The access
token is held in memory only; no tokens are written to `localStorage`.

The tech stack mirrors `ugsys-projects-registry/web` exactly: React 19 + TypeScript, Vite,
Tailwind CSS v4, react-router-dom v7, nanostores + @nanostores/react, `@ugsys/ui-lib` shared
components, Vitest + React Testing Library, and pnpm.

---

## Architecture

### Component Tree

```
main.tsx
└── RouterProvider (router.tsx)
    └── Layout
        ├── Navbar (@ugsys/ui-lib) + UserMenu (@ugsys/ui-lib)
        ├── AuthGate                        ← blocks render until auth resolved
        │   └── ProfilePage
        │       ├── AvatarUploader
        │       ├── PersonalSection
        │       ├── ContactSection
        │       ├── DisplaySection
        │       └── PreferencesSection
        └── Footer (@ugsys/ui-lib)
```

### Data Flow

```
Browser startup
  └─► initializeAuth()
        ├─ POST /api/v1/auth/refresh  (credentials: include)
        │   ├─ 200 → set $accessToken + $user → render ProfilePage
        │   └─ non-200 → redirect to login
        └─ $isInitializing = true while in-flight

ProfilePage mount
  └─► loadProfile()
        ├─ GET /api/v1/profiles/me  (Authorization: Bearer)
        │   ├─ 200 → $profile.set(data)
        │   └─ non-200 → toast error
        └─ $profileLoading = true while in-flight

Edit Section submit (optimistic)
  ├─ snapshot = $profile.get()
  ├─ $profile.set(optimisticValue)   ← immediate UI update
  ├─ PATCH /api/v1/profiles/{id}/…
  │   ├─ 200 → keep optimistic value, close edit mode
  │   └─ non-200 → $profile.set(snapshot), toast error
  └─ disable submit while in-flight
```

---

## File / Directory Structure

```
web/
├── src/
│   ├── app/
│   │   └── router.tsx                  # single route: /
│   ├── components/
│   │   ├── layout/
│   │   │   ├── Layout.tsx              # Navbar + Footer shell
│   │   │   └── AuthGate.tsx            # loading spinner / redirect guard
│   │   ├── profile/
│   │   │   ├── PersonalSection.tsx
│   │   │   ├── ContactSection.tsx
│   │   │   ├── DisplaySection.tsx
│   │   │   ├── PreferencesSection.tsx
│   │   │   └── AvatarUploader.tsx
│   │   └── ui/
│   │       └── Toast.tsx               # toast item + container
│   ├── hooks/
│   │   └── useEditSection.ts           # shared read/edit toggle + optimistic logic
│   ├── pages/
│   │   └── ProfilePage.tsx
│   ├── services/
│   │   ├── httpClient.ts               # fetch wrapper (cookie-aware, no refresh loop)
│   │   ├── authService.ts              # refresh + logout calls to identity-manager
│   │   └── profileService.ts           # all /api/v1/profiles/* calls
│   ├── stores/
│   │   ├── authStore.ts                # $user, $accessToken, $isInitializing
│   │   └── profileStore.ts             # $profile, $profileLoading, $profileError
│   ├── types/
│   │   ├── auth.ts
│   │   └── profile.ts
│   ├── utils/
│   │   └── toast.ts                    # $toasts atom + addToast / dismissToast
│   ├── index.css
│   └── main.tsx
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
└── vitest.config.ts
```

---

## Store Design

### authStore (`src/stores/authStore.ts`)

```typescript
import { atom, computed } from 'nanostores';

// In-memory only — never written to localStorage
let _accessToken: string | null = null;

export function getAccessToken(): string | null { return _accessToken; }
export function setAccessToken(t: string): void  { _accessToken = t; }
export function clearAccessToken(): void          { _accessToken = null; }

export interface AuthUser { sub: string; email: string; roles: string[]; }

export const $user            = atom<AuthUser | null>(null);
export const $isInitializing  = atom<boolean>(true);   // true until refresh resolves
export const $isAuthenticated = computed($user, (u) => u !== null);

/**
 * Called once in main.tsx before rendering.
 * Calls POST /api/v1/auth/refresh with credentials:'include'.
 * On 200 → stores access token in memory + sets $user.
 * On non-200 → redirects to Identity Manager login URL.
 */
export async function initializeAuth(): Promise<void> { /* implemented in authStore.ts */ }

/** Clears in-memory token, calls authService.logout(), redirects to login. */
export async function logout(): Promise<void> { /* implemented in authStore.ts */ }
```

Key difference from registry `authStore`: `initializeAuth()` is **not** a no-op. It performs
the cookie-based refresh call. There is no `_refreshToken` in memory because the refresh token
lives exclusively in the `httpOnly` cookie managed by the browser.

### profileStore (`src/stores/profileStore.ts`)

```typescript
import { atom } from 'nanostores';
import type { ProfileResponse } from '../types/profile';

export const $profile        = atom<ProfileResponse | null>(null);
export const $profileLoading = atom<boolean>(false);
export const $profileError   = atom<string | null>(null);

/** Calls GET /api/v1/profiles/me and populates $profile. */
export async function loadProfile(): Promise<void> { /* implemented in profileStore.ts */ }
```

### toastStore (`src/utils/toast.ts`)

```typescript
import { atom } from 'nanostores';

export interface Toast {
  id: string;
  message: string;
  type: 'error' | 'success' | 'info';
}

export const $toasts = atom<Toast[]>([]);

export function addToast(message: string, type: Toast['type'] = 'error'): void {
  const current = $toasts.get();
  if (current.length >= 3) return; // cap at 3; auto-dismiss frees slots
  const id = crypto.randomUUID();
  $toasts.set([...current, { id, message, type }]);
  setTimeout(() => dismissToast(id), 5_000);
}

export function dismissToast(id: string): void {
  $toasts.set($toasts.get().filter((t) => t.id !== id));
}
```

---

## Service Layer Design

### httpClient (`src/services/httpClient.ts`)

Mirrors the registry `httpClient` with one critical difference: **no bearer refresh-token
loop**. Because the refresh token is a `httpOnly` cookie, the 401 interceptor calls
`authService.refresh()` (which uses `credentials: 'include'`) instead of passing a bearer
refresh token in the request body.

```
VITE_API_BASE_URL  — profile-service origin (same origin in prod, proxy in dev)
VITE_AUTH_API_URL  — identity-manager origin (https://auth.apps.cloud.org.bo)
TIMEOUT            — 15 000 ms via AbortController
```

On 401 from any profile API call:
1. Call `authService.refresh()` once (cookie-based).
2. On success: update `_accessToken`, retry original request.
3. On failure: `clearAccessToken()`, redirect to login.

### authService (`src/services/authService.ts`)

```typescript
const AUTH_BASE = import.meta.env.VITE_AUTH_API_URL ?? '';

export const authService = {
  /** Cookie-based refresh — no body, credentials: 'include' */
  async refresh(): Promise<{ access_token: string }>,

  /** Cookie-based logout — credentials: 'include', best-effort */
  async logout(): Promise<void>,
};
```

Both calls use raw `fetch` (not `httpClient`) to avoid circular dependency and to ensure
`credentials: 'include'` is always set regardless of `httpClient` configuration.

### profileService (`src/services/profileService.ts`)

```typescript
export const profileService = {
  getMe(): Promise<ProfileResponse>,
  updatePersonal(userId: string, body: UpdatePersonalRequest): Promise<ProfileResponse>,
  updateContact(userId: string, body: UpdateContactRequest): Promise<ProfileResponse>,
  updateDisplay(userId: string, body: UpdateDisplayRequest): Promise<ProfileResponse>,
  updatePreferences(userId: string, body: UpdatePreferencesRequest): Promise<ProfileResponse>,
  uploadAvatar(userId: string, file: File): Promise<ProfileResponse>,
  deleteAvatar(userId: string): Promise<void>,
};
```

`uploadAvatar` uses `FormData` and omits the `Content-Type` header so the browser sets the
correct `multipart/form-data` boundary automatically.

---

## Component Design

### AuthGate (`src/components/layout/AuthGate.tsx`)

```typescript
interface AuthGateProps { children: React.ReactNode; }
```

Reads `$isInitializing` and `$isAuthenticated` via `useStore`.

- `$isInitializing === true` → renders full-page spinner, no children.
- `$isInitializing === false && $isAuthenticated === false` → redirect is already handled
  inside `initializeAuth()`; AuthGate renders nothing as a safety net.
- `$isAuthenticated === true` → renders `children`.

### ProfilePage (`src/pages/ProfilePage.tsx`)

No props. Calls `loadProfile()` on mount via `useEffect`. Reads `$profile`, `$profileLoading`.
Renders `AvatarUploader` at the top, then the four edit sections in a single-column layout.
Shows a skeleton loader while `$profileLoading` is true.

### useEditSection hook (`src/hooks/useEditSection.ts`)

```typescript
interface UseEditSectionOptions<T> {
  currentValue: T;
  onSave: (value: T) => Promise<ProfileResponse>;
  validate?: (value: T) => string | null;
}

interface UseEditSectionResult<T> {
  isEditing: boolean;
  isSaving: boolean;
  draft: T;
  setDraft: (v: T) => void;
  startEdit: () => void;
  cancelEdit: () => void;
  submitEdit: () => Promise<void>;
  validationError: string | null;
}
```

The hook encapsulates the full optimistic-update cycle:

1. `startEdit()` — `isEditing = true`, copies `currentValue` into `draft`.
2. `submitEdit()`:
   - Runs `validate(draft)` — if error, sets `validationError`, returns early (no API call).
   - Takes `snapshot = $profile.get()`.
   - Applies `$profile.set({ ...snapshot, ...draft })` (optimistic).
   - Sets `isSaving = true`.
   - Calls `onSave(draft)`.
   - On success: `$profile.set(response)`, `isEditing = false`.
   - On error: `$profile.set(snapshot)`, `addToast(...)`.
   - Always: `isSaving = false`.
3. `cancelEdit()` — `isEditing = false`, discards draft.

### PersonalSection

Fields: `full_name` (text), `date_of_birth` (date).
Validation: `full_name.trim().length > 0`.
API call: `profileService.updatePersonal(userId, { full_name, date_of_birth })`.

### ContactSection

Fields: `phone` (text), `street`, `city`, `state`, `postal_code`, `country` (all text).
No client-side validation beyond what the server enforces.
API call: `profileService.updateContact(userId, { phone, address: { ... } })`.

### DisplaySection

Fields: `bio` (textarea), `display_name` (text).
Live counter: `data-testid="bio-counter"` shows `500 - bio.length`.
Validation: `bio === null || bio.length <= 500`.
API call: `profileService.updateDisplay(userId, { bio, display_name })`.

### PreferencesSection

Fields: three `<input type="checkbox">` for notification toggles, `<select>` for language
(ISO 639-1 codes), `<select>` for timezone (IANA identifiers).
API call: `profileService.updatePreferences(userId, { notification_preferences, language, timezone })`.

### AvatarUploader (`src/components/profile/AvatarUploader.tsx`)

```typescript
interface AvatarUploaderProps {
  avatarUrl: string | null;
  userId: string;
}
```

Internal state: `preview: string | null`, `pendingFile: File | null`, `isUploading: boolean`.

Flow:
1. Click avatar → trigger hidden `<input type="file" accept="image/jpeg,image/png,image/webp">`.
2. `onChange`:
   - If `file.size > 5_242_880` → `addToast('El archivo supera el límite de 5 MB')`, return.
   - If `!['image/jpeg','image/png','image/webp'].includes(file.type)` → `addToast(...)`, return.
   - `preview = URL.createObjectURL(file)`, `pendingFile = file`.
3. Render preview with Confirm / Cancel buttons.
4. Confirm → `isUploading = true`, call `profileService.uploadAvatar(userId, pendingFile)`.
   - 200: `$profile.set({ ...$profile.get(), avatar_url: response.avatar_url })`,
     `URL.revokeObjectURL(preview)`, clear state.
   - Error: `addToast(...)`, clear preview state.
5. Delete button (shown when `avatarUrl !== null`) → call `profileService.deleteAvatar(userId)`.
   - 200: `$profile.set({ ...$profile.get(), avatar_url: null })`.
   - Error: `addToast(...)`.

### Toast (`src/components/ui/Toast.tsx`)

`ToastContainer` reads `$toasts` via `useStore` and renders up to 3 items in a fixed
bottom-right stack. Each `Toast` item has a dismiss button and fades out on removal.

---

## Router and Auth Gate

```typescript
// src/app/router.tsx
import { createBrowserRouter } from 'react-router-dom';
import Layout from '@/components/layout/Layout';
import ProfilePage from '@/pages/ProfilePage';

export const router = createBrowserRouter([
  {
    element: <Layout />,
    children: [
      { path: '/', element: <ProfilePage /> },
    ],
  },
]);
```

`main.tsx` calls `await initializeAuth()` before `ReactDOM.createRoot(...).render(...)`.
`Layout` wraps `<Outlet />` in `<AuthGate>` to block rendering until auth resolves.

`UserMenu` props in `Layout`:
```typescript
<UserMenu
  profileHref="https://profile.apps.cloud.org.bo"
  adminPanelUrl="https://admin.apps.cloud.org.bo"
  user={$user}
  onLogout={logout}
  renderLink={({ href, children }) => <NavLink to={href}>{children}</NavLink>}
/>
```

---

## Data Models

### `src/types/profile.ts`

```typescript
export interface AddressResponse {
  street: string; city: string; state: string;
  postal_code: string; country: string;
}

export interface NotificationPreferencesResponse {
  email: boolean; sms: boolean; whatsapp: boolean;
}

export interface ProfileResponse {
  user_id: string; email: string; full_name: string;
  phone: string; date_of_birth: string;
  address: AddressResponse;
  email_verified: boolean;
  avatar_url: string | null;
  bio: string | null; display_name: string | null;
  language: string; timezone: string;
  notification_preferences: NotificationPreferencesResponse;
  deleted_at: string | null;
}

export interface UpdatePersonalRequest  { full_name: string; date_of_birth: string; }
export interface UpdateContactRequest   { phone: string; address: AddressResponse; }
export interface UpdateDisplayRequest   { bio: string | null; display_name: string | null; }
export interface UpdatePreferencesRequest {
  notification_preferences: NotificationPreferencesResponse;
  language: string; timezone: string;
}
```

### `src/types/auth.ts`

```typescript
export interface AuthUser { sub: string; email: string; roles: string[]; }
```

---

## Error Handling

- All `profileService` calls are wrapped in try/catch inside `useEditSection` and `loadProfile`.
- Errors surface via `addToast()` with a human-readable Spanish message.
- Toast messages never include HTTP status codes, field names, stack traces, or server error text.
- `httpClient` extracts `user_message` from the ugsys error envelope; if absent, falls back to
  a generic "No se pudo completar la solicitud" string.
- 401 from profile API → `httpClient` attempts one cookie-based refresh → retries → on second
  401 redirects to login.
- Avatar upload errors clear `preview` and `pendingFile` so the user can retry cleanly.
- `GET /api/v1/profiles/me` returning 401 → redirect to login (handled by `httpClient`).
- `GET /api/v1/profiles/me` returning other non-200 → toast error, `$profile` stays null,
  no stale data rendered.

---

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions
of a system — essentially, a formal statement about what the system should do. Properties serve
as the bridge between human-readable specifications and machine-verifiable correctness
guarantees.*

### Property 1: Non-200 Refresh Redirects to Login

*For any* call to `initializeAuth()` where the refresh response has a status code other than
200, the function SHALL set `window.location.href` to the Identity Manager login URL and SHALL
NOT set `$user` to a non-null value.

**Validates: Requirements 1.3, 1.5**

---

### Property 2: Display Fidelity

*For any* `ProfileResponse` returned by `GET /api/v1/profiles/me`, every field in the response
SHALL appear in the rendered output of `ProfilePage` — the rendered text for each field SHALL
equal the corresponding value in the response object.

**Validates: Requirements 2.2, 10.1**

---

### Property 3: Optimistic Update Applied Immediately

*For any* edit section and any draft value submitted, the `$profile` store SHALL reflect the
submitted values synchronously before the PATCH response is received.

**Validates: Requirements 3.3, 4.3, 5.5, 6.3**

---

### Property 4: Successful-Update Consistency

*For any* edit section submission that receives an HTTP 200 response, the value displayed in
the profile page after the response SHALL equal the value that was submitted.

**Validates: Requirements 3.4, 4.4, 5.6, 6.4, 10.2**

---

### Property 5: Revert-on-Error

*For any* edit section submission that receives a non-200 response, the value displayed in the
profile page after the response SHALL equal the value that was displayed before the edit was
activated (the pre-edit snapshot).

**Validates: Requirements 3.5, 4.5, 5.7, 6.5, 10.3**

---

### Property 6: Bio Character Counter Accuracy

*For any* string of length N typed into the bio field (where N ≤ 500), the character counter
SHALL display exactly `500 - N` characters remaining.

**Validates: Requirements 5.2**

---

### Property 7: Bio Length Validation

*For any* bio string whose length exceeds 500 characters, the submit button SHALL be disabled
and no PATCH request SHALL be sent.

**Validates: Requirements 5.3**

---

### Property 8: full_name Non-Empty Validation

*For any* string composed entirely of whitespace (including the empty string) entered as
`full_name`, the submit button SHALL be disabled and no PATCH request SHALL be sent.

**Validates: Requirements 3.6**

---

### Property 9: Invalid Avatar File Rejected Client-Side

*For any* file whose size exceeds 5 MB or whose MIME type is not `image/jpeg`, `image/png`,
or `image/webp`, the `AvatarUploader` SHALL reject the file, SHALL NOT call
`POST /api/v1/profiles/{user_id}/avatar`, and SHALL display a toast notification.

**Validates: Requirements 7.2, 7.3, 10.5**

---

### Property 10: Toast Safety

*For any* non-200 API response, the toast message displayed to the user SHALL NOT contain
HTTP status codes, stack traces, server error messages, or internal field names.

**Validates: Requirements 9.1, 9.2**

---

### Property 11: Toast Maximum Simultaneous Count

*For any* sequence of more than 3 rapid `addToast()` calls, the number of toasts visible
simultaneously SHALL never exceed 3.

**Validates: Requirements 9.4**

---

### Property 12: Toast Auto-Dismiss

*For any* toast added via `addToast()`, the toast SHALL be removed from `$toasts` after
5000 milliseconds if not manually dismissed earlier.

**Validates: Requirements 9.3**

---

### Property 13: Authentication Gate

*For any* render of the application where `$isAuthenticated` is false and `$isInitializing`
is false, no profile content SHALL be rendered and the browser SHALL be redirected to the
Identity Manager login URL.

**Validates: Requirements 1.3, 1.5, 10.4**

---

## Testing Strategy

### Dual Testing Approach

Both unit/example tests and property-based tests are required and complementary: unit tests
catch concrete bugs in specific scenarios; property tests verify universal correctness across
all inputs.

### Property-Based Testing Library

Use **fast-check** (`pnpm add -D fast-check`). Each property test runs a minimum of **100
iterations** (`{ numRuns: 100 }`).

Tag format for each property test:
```
// Feature: profile-frontend, Property N: <property_text>
```

### Unit Tests (Vitest + React Testing Library)

One test file per module. Focus on specific examples, integration points, and edge cases.
Avoid testing multiple failure modes in a single test.

| Test file | What it covers |
|-----------|----------------|
| `authStore.test.ts` | `initializeAuth` 200 path, 401 path, non-200 path, loading state |
| `profileStore.test.ts` | `loadProfile` success, 401 redirect, non-200 toast |
| `toast.test.ts` | `addToast`, `dismissToast`, max-3 cap, auto-dismiss timer |
| `useEditSection.test.ts` | optimistic apply, revert on error, validation blocking |
| `PersonalSection.test.tsx` | read mode render, edit mode fields, empty name blocked |
| `DisplaySection.test.tsx` | bio counter display, 500-char submission block |
| `AvatarUploader.test.tsx` | valid file preview, size rejection, MIME rejection |
| `AuthGate.test.tsx` | spinner while initializing, no content when unauthenticated |
| `ProfilePage.test.tsx` | full render with mocked store, all fields visible |

### Property-Based Tests (fast-check)

```typescript
// Feature: profile-frontend, Property 2: Display Fidelity
it('renders every field from any ProfileResponse', () => {
  fc.assert(fc.property(arbitraryProfileResponse(), (profile) => {
    mockGetMe(profile);
    const { getByText } = render(<ProfilePage />);
    expect(getByText(profile.full_name)).toBeInTheDocument();
    expect(getByText(profile.email)).toBeInTheDocument();
    // ... all scalar fields
  }), { numRuns: 100 });
});

// Feature: profile-frontend, Property 5: Revert-on-Error
it('reverts $profile to pre-edit snapshot on any non-200 PATCH', () => {
  fc.assert(fc.property(
    arbitraryProfileResponse(),
    arbitraryPersonalDraft(),
    fc.integer({ min: 400, max: 599 }),
    (profile, draft, errorStatus) => {
      $profile.set(profile);
      const snapshot = { ...profile };
      mockPatch(errorStatus);
      await submitPersonalEdit(draft);
      expect($profile.get()).toEqual(snapshot);
    }
  ), { numRuns: 100 });
});

// Feature: profile-frontend, Property 9: Invalid Avatar File Rejected
it('rejects any file > 5MB or with invalid MIME type', () => {
  fc.assert(fc.property(
    fc.oneof(arbitraryOversizedFile(), arbitraryInvalidMimeFile()),
    (file) => {
      const fetchSpy = vi.spyOn(global, 'fetch');
      fireEvent.change(avatarInput, { target: { files: [file] } });
      expect(fetchSpy).not.toHaveBeenCalled();
      expect($toasts.get().length).toBeGreaterThan(0);
    }
  ), { numRuns: 100 });
});

// Feature: profile-frontend, Property 6: Bio Character Counter Accuracy
it('counter shows 500 - N for any bio of length N <= 500', () => {
  fc.assert(fc.property(
    fc.string({ maxLength: 500 }),
    (bio) => {
      const { getByTestId } = render(<DisplaySection profile={mockProfile} userId="u1" />);
      userEvent.click(screen.getByRole('button', { name: /editar/i }));
      fireEvent.change(screen.getByRole('textbox', { name: /bio/i }), { target: { value: bio } });
      expect(getByTestId('bio-counter').textContent).toBe(String(500 - bio.length));
    }
  ), { numRuns: 100 });
});

// Feature: profile-frontend, Property 11: Toast Maximum Simultaneous Count
it('never shows more than 3 toasts simultaneously', () => {
  fc.assert(fc.property(
    fc.array(fc.string({ minLength: 1 }), { minLength: 4, maxLength: 20 }),
    (messages) => {
      $toasts.set([]);
      messages.forEach((m) => addToast(m));
      expect($toasts.get().length).toBeLessThanOrEqual(3);
    }
  ), { numRuns: 100 });
});

// Feature: profile-frontend, Property 12: Toast Auto-Dismiss
it('removes any toast after 5000ms', () => {
  fc.assert(fc.property(fc.string({ minLength: 1 }), (message) => {
    vi.useFakeTimers();
    $toasts.set([]);
    addToast(message);
    expect($toasts.get().length).toBe(1);
    vi.advanceTimersByTime(5_000);
    expect($toasts.get().length).toBe(0);
    vi.useRealTimers();
  }), { numRuns: 100 });
});
```

### Coverage Gate

- Unit tests: **80% minimum** (CI blocks merge below this)
- Target: **90%+** for stores, hooks, and services
- Property tests: not counted toward coverage gate but required for all 13 properties above
- Integration tests: not counted toward coverage gate; run separately against a local dev server
