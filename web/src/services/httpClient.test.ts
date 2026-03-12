import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

// Mock authService before importing httpClient
vi.mock('./authService', () => ({
  authService: {
    refresh: vi.fn(),
    logout: vi.fn(),
  },
}));

import { authService } from './authService';
import { apiFetch } from './httpClient';
import { setAccessToken, clearAccessToken, getAccessToken } from '../stores/authStore';

// Minimal valid JWT
function makeJwt(): string {
  const h = btoa(JSON.stringify({ alg: 'RS256' }));
  const p = btoa(
    JSON.stringify({
      sub: 'u1',
      email: 'a@b.com',
      roles: [],
      exp: Math.floor(Date.now() / 1000) + 3600,
    })
  );
  return `${h}.${p}.sig`;
}

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
  clearAccessToken();
  vi.clearAllMocks();
  Object.defineProperty(window, 'location', { value: { href: '' }, writable: true });
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('apiFetch.get — success', () => {
  it('returns data from response envelope', async () => {
    mockFetch(200, { data: { id: '1', name: 'Test' } });
    const result = await apiFetch.get<{ id: string; name: string }>('/api/v1/test');
    expect(result).toEqual({ id: '1', name: 'Test' });
  });

  it('returns raw body when no data envelope', async () => {
    mockFetch(200, { id: '1', name: 'Test' });
    const result = await apiFetch.get<{ id: string; name: string }>('/api/v1/test');
    expect(result).toEqual({ id: '1', name: 'Test' });
  });

  it('injects Authorization header when token is set', async () => {
    const token = makeJwt();
    setAccessToken(token);
    mockFetch(200, { data: {} });
    await apiFetch.get('/api/v1/test');
    const fetchCall = vi.mocked(fetch).mock.calls[0];
    const headers = fetchCall[1]?.headers as Record<string, string>;
    expect(headers['Authorization']).toBe(`Bearer ${token}`);
  });
});

describe('apiFetch.get — error handling', () => {
  it('throws with user_message from error envelope', async () => {
    mockFetch(422, { user_message: 'Datos inválidos' });
    await expect(apiFetch.get('/api/v1/test')).rejects.toThrow('Datos inválidos');
  });

  it('throws with message field when user_message absent', async () => {
    mockFetch(500, { message: 'Error interno' });
    await expect(apiFetch.get('/api/v1/test')).rejects.toThrow('Error interno');
  });

  it('throws generic message when body is empty', async () => {
    mockFetch(500, null);
    await expect(apiFetch.get('/api/v1/test')).rejects.toThrow('No se pudo completar la solicitud');
  });

  it('throws with detail string', async () => {
    mockFetch(400, { detail: 'Campo requerido' });
    await expect(apiFetch.get('/api/v1/test')).rejects.toThrow('Campo requerido');
  });
});

describe('apiFetch — 401 retry', () => {
  it('retries once after successful token refresh on 401', async () => {
    const newToken = makeJwt();
    vi.mocked(authService.refresh).mockResolvedValue({ access_token: newToken });

    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ ok: false, status: 401, json: () => Promise.resolve({}) })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ data: { ok: true } }),
      });
    vi.stubGlobal('fetch', fetchMock);

    const result = await apiFetch.get<{ ok: boolean }>('/api/v1/test');
    expect(result).toEqual({ ok: true });
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(getAccessToken()).toBe(newToken);
  });

  it('redirects to login when refresh fails on 401', async () => {
    vi.mocked(authService.refresh).mockRejectedValue(new Error('Refresh failed'));

    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: false, status: 401, json: () => Promise.resolve({}) })
    );

    await expect(apiFetch.get('/api/v1/test')).rejects.toThrow();
    expect(window.location.href).toContain('login');
  });

  it('does not retry a second 401 (isRetry guard)', async () => {
    vi.mocked(authService.refresh).mockResolvedValue({ access_token: makeJwt() });

    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      json: () => Promise.resolve({}),
    });
    vi.stubGlobal('fetch', fetchMock);

    await expect(apiFetch.get('/api/v1/test')).rejects.toThrow();
    // first call + one retry = 2 total
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});

describe('apiFetch.patch', () => {
  it('sends JSON body', async () => {
    mockFetch(200, { data: {} });
    await apiFetch.patch('/api/v1/test', { name: 'Dev' });
    const fetchCall = vi.mocked(fetch).mock.calls[0];
    expect(fetchCall[1]?.body).toBe(JSON.stringify({ name: 'Dev' }));
    const headers = fetchCall[1]?.headers as Record<string, string>;
    expect(headers['Content-Type']).toBe('application/json');
  });
});

describe('apiFetch.postForm', () => {
  it('sends FormData without Content-Type header', async () => {
    mockFetch(200, { data: {} });
    const fd = new FormData();
    fd.append('file', new Blob(['x'], { type: 'image/jpeg' }), 'photo.jpg');
    await apiFetch.postForm('/api/v1/test', fd);
    const fetchCall = vi.mocked(fetch).mock.calls[0];
    const headers = fetchCall[1]?.headers as Record<string, string>;
    expect(headers['Content-Type']).toBeUndefined();
  });
});

describe('apiFetch.delete', () => {
  it('sends DELETE request', async () => {
    mockFetch(200, null);
    await apiFetch.delete('/api/v1/test');
    const fetchCall = vi.mocked(fetch).mock.calls[0];
    expect(fetchCall[1]?.method).toBe('DELETE');
  });
});
