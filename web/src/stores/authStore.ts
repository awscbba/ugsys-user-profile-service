import { atom, computed } from 'nanostores';
import type { AuthUser } from '../types/auth';
import { authService } from '../services/authService';

// ── In-memory token — never written to localStorage ───────────────────────────

let _accessToken: string | null = null;

export function getAccessToken(): string | null {
  return _accessToken;
}
export function setAccessToken(t: string): void {
  _accessToken = t;
}
export function clearAccessToken(): void {
  _accessToken = null;
}

// ── Atoms ─────────────────────────────────────────────────────────────────────

export const $user = atom<AuthUser | null>(null);
export const $isInitializing = atom<boolean>(true); // true until refresh resolves
export const $isAuthenticated = computed($user, (u) => u !== null);

// ── Helpers ───────────────────────────────────────────────────────────────────

const LOGIN_URL = `${import.meta.env.VITE_AUTH_API_URL ?? 'https://auth.apps.cloud.org.bo'}/login?redirect=${encodeURIComponent(typeof window !== 'undefined' ? window.location.origin : 'https://profile.apps.cloud.org.bo')}`;

function decodeJwtPayload(token: string): Record<string, unknown> {
  const base64 = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
  return JSON.parse(atob(base64));
}

function extractUser(token: string): AuthUser | null {
  try {
    const payload = decodeJwtPayload(token);
    const exp = payload['exp'];
    if (typeof exp === 'number' && exp * 1000 < Date.now()) return null;
    const sub = payload['sub'];
    const email = payload['email'];
    const roles = payload['roles'] ?? payload['cognito:groups'] ?? [];
    if (typeof sub !== 'string' || typeof email !== 'string') return null;
    return { sub, email, roles: Array.isArray(roles) ? (roles as string[]) : [] };
  } catch {
    return null;
  }
}

// ── Actions ───────────────────────────────────────────────────────────────────

/**
 * Called once in main.tsx before rendering.
 * On 200 → stores access token + sets $user.
 * On non-200 → redirects to Identity Manager login URL.
 */
export async function initializeAuth(): Promise<void> {
  $isInitializing.set(true);
  try {
    const data = await authService.refresh();
    setAccessToken(data.access_token);
    $user.set(extractUser(data.access_token));
  } catch {
    // non-200 or network error → redirect to login
    $user.set(null);
    window.location.href = LOGIN_URL;
  } finally {
    $isInitializing.set(false);
  }
}

/** Clears in-memory token, calls authService.logout(), redirects to login. */
export async function logout(): Promise<void> {
  clearAccessToken();
  $user.set(null);
  await authService.logout();
  window.location.href = LOGIN_URL;
}
