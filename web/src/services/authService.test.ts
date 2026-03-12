import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { authService } from './authService';

function mockFetch(status: number, body: unknown): void {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok: status >= 200 && status < 300,
      status,
      json: () => Promise.resolve(body),
    })
  );
}

beforeEach(() => {
  vi.clearAllMocks();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('authService.refresh', () => {
  it('returns access_token on 200 with data envelope', async () => {
    mockFetch(200, { data: { access_token: 'tok123' } });
    const result = await authService.refresh();
    expect(result.access_token).toBe('tok123');
  });

  it('returns access_token on 200 without data envelope', async () => {
    mockFetch(200, { access_token: 'tok456' });
    const result = await authService.refresh();
    expect(result.access_token).toBe('tok456');
  });

  it('throws on non-200', async () => {
    mockFetch(401, {});
    await expect(authService.refresh()).rejects.toThrow('Token refresh failed');
  });

  it('sends credentials: include', async () => {
    mockFetch(200, { access_token: 'tok' });
    await authService.refresh();
    const call = vi.mocked(fetch).mock.calls[0];
    expect(call[1]?.credentials).toBe('include');
  });
});

describe('authService.logout', () => {
  it('calls logout endpoint with credentials: include', async () => {
    mockFetch(200, {});
    await authService.logout();
    const call = vi.mocked(fetch).mock.calls[0];
    expect(call[0] as string).toContain('/api/v1/auth/logout');
    expect(call[1]?.credentials).toBe('include');
  });

  it('does not throw when logout endpoint fails (best-effort)', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('Network error')));
    await expect(authService.logout()).resolves.toBeUndefined();
  });
});
