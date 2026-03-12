/**
 * authService — uses raw fetch (not httpClient) to avoid circular dependency.
 * Both calls use credentials:'include' so the httpOnly cookie is sent automatically.
 */

const AUTH_BASE = import.meta.env.VITE_AUTH_API_URL ?? '';

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  require_password_change?: boolean;
}

export const authService = {
  /** Authenticate with email + password. Sets httpOnly refresh cookie on success. */
  async login(email: string, password: string): Promise<LoginResponse> {
    const response = await fetch(`${AUTH_BASE}/api/v1/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ email, password }),
    });
    const json = await response.json().catch(() => null);
    if (!response.ok) {
      const msg =
        (json as { message?: string; detail?: string } | null)?.message ??
        (json as { message?: string; detail?: string } | null)?.detail ??
        'Credenciales inválidas';
      throw new Error(typeof msg === 'string' ? msg : 'Credenciales inválidas');
    }
    return ((json as { data?: LoginResponse }).data ?? json) as LoginResponse;
  },

  /** Cookie-based refresh — no body, credentials: 'include' */
  async refresh(): Promise<{ access_token: string }> {
    const response = await fetch(`${AUTH_BASE}/api/v1/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
    });
    if (!response.ok) {
      throw new Error('Token refresh failed');
    }
    const json = await response.json();
    return (json.data ?? json) as { access_token: string };
  },

  /** Cookie-based logout — credentials: 'include', best-effort */
  async logout(): Promise<void> {
    try {
      await fetch(`${AUTH_BASE}/api/v1/auth/logout`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
      });
    } catch {
      // best-effort — session already cleared client-side
    }
  },
};
