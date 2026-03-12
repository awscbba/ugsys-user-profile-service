import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import * as fc from 'fast-check';

// Mock authService before importing authStore
vi.mock('../services/authService', () => ({
  authService: {
    refresh: vi.fn(),
    logout: vi.fn(),
  },
}));

import { authService } from '../services/authService';
import {
  $user,
  $isInitializing,
  $isAuthenticated,
  getAccessToken,
  clearAccessToken,
  initializeAuth,
  logout,
} from './authStore';

// Minimal valid JWT with sub + email + roles (exp far in future)
function makeJwt(payload: Record<string, unknown>): string {
  const header = btoa(JSON.stringify({ alg: 'RS256', typ: 'JWT' }));
  const body = btoa(JSON.stringify({ exp: Math.floor(Date.now() / 1000) + 3600, ...payload }));
  return `${header}.${body}.sig`;
}

const VALID_TOKEN = makeJwt({ sub: 'user-1', email: 'dev@example.com', roles: ['member'] });

beforeEach(() => {
  clearAccessToken();
  $user.set(null);
  $isInitializing.set(true);
  vi.clearAllMocks();
  // Reset location.href spy
  Object.defineProperty(window, 'location', {
    value: { href: '' },
    writable: true,
  });
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('initializeAuth — 200 path', () => {
  it('stores access token in memory and sets $user', async () => {
    vi.mocked(authService.refresh).mockResolvedValue({ access_token: VALID_TOKEN });
    await initializeAuth();
    expect(getAccessToken()).toBe(VALID_TOKEN);
    expect($user.get()).not.toBeNull();
    expect($user.get()?.email).toBe('dev@example.com');
    expect($isInitializing.get()).toBe(false);
  });

  it('sets $isAuthenticated to true after 200', async () => {
    vi.mocked(authService.refresh).mockResolvedValue({ access_token: VALID_TOKEN });
    await initializeAuth();
    expect($isAuthenticated.get()).toBe(true);
  });
});

describe('initializeAuth — non-200 path', () => {
  it('redirects to login and keeps $user null on 401', async () => {
    vi.mocked(authService.refresh).mockRejectedValue(new Error('Token refresh failed'));
    await initializeAuth();
    expect($user.get()).toBeNull();
    expect(window.location.href).toContain('login');
    expect($isInitializing.get()).toBe(false);
  });
});

describe('logout', () => {
  it('clears token, sets $user null, and redirects', async () => {
    vi.mocked(authService.refresh).mockResolvedValue({ access_token: VALID_TOKEN });
    vi.mocked(authService.logout).mockResolvedValue(undefined);
    await initializeAuth();
    await logout();
    expect(getAccessToken()).toBeNull();
    expect($user.get()).toBeNull();
    expect(window.location.href).toContain('login');
  });
});

describe('$isAuthenticated computed', () => {
  it('is false when $user is null', () => {
    $user.set(null);
    expect($isAuthenticated.get()).toBe(false);
  });

  it('is true when $user is set', () => {
    $user.set({ sub: 'u1', email: 'a@b.com', roles: [] });
    expect($isAuthenticated.get()).toBe(true);
  });
});

// Feature: profile-frontend, Property 1: Non-200 Refresh Redirects to Login
describe('Property 1: Non-200 Refresh Redirects to Login', () => {
  it('redirects to login and keeps $user null for any non-200 status', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.integer({ min: 201, max: 599 }).filter((s) => s !== 200),
        async (_status) => {
          clearAccessToken();
          $user.set(null);
          $isInitializing.set(true);
          Object.defineProperty(window, 'location', { value: { href: '' }, writable: true });

          vi.mocked(authService.refresh).mockRejectedValue(new Error('Token refresh failed'));
          await initializeAuth();

          expect($user.get()).toBeNull();
          expect(window.location.href).toContain('login');
        }
      ),
      { numRuns: 100 }
    );
  });
});
