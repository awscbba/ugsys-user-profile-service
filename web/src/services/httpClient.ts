/**
 * HTTP client for the profile-service API.
 * - Injects Authorization: Bearer from in-memory authStore
 * - 15 000 ms timeout via AbortController
 * - 401 interceptor: calls authService.refresh() once (cookie-based), retries on success,
 *   redirects to login on second 401
 * - Extracts user_message from ugsys error envelope; falls back to generic Spanish message
 */

import { getAccessToken, setAccessToken, clearAccessToken } from '../stores/authStore';
import { authService } from './authService';

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '';
const TIMEOUT_MS = 15_000;

const LOGIN_URL = '/login';

function redirectToLogin(): void {
  clearAccessToken();
  window.location.href = LOGIN_URL;
}

function buildHeaders(token: string | null, includeContentType = true): Record<string, string> {
  const headers: Record<string, string> = {
    'X-Request-ID': crypto.randomUUID(),
  };
  if (includeContentType) {
    headers['Content-Type'] = 'application/json';
  }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

type ErrorBody = {
  message?: string; // ugsys user_message field
  user_message?: string; // alternative ugsys field
  error?: string;
  detail?: string | { msg: string }[];
} | null;

function extractUserMessage(body: ErrorBody): string {
  if (!body) return 'No se pudo completar la solicitud';
  if (body.user_message) return body.user_message;
  if (body.message) return body.message;
  if (typeof body.detail === 'string') return body.detail;
  if (Array.isArray(body.detail) && body.detail.length > 0) return body.detail[0].msg;
  return 'No se pudo completar la solicitud';
}

async function fetchWithTimeout(url: string, options: RequestInit): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } finally {
    clearTimeout(timer);
  }
}

async function parseResponse<T>(response: Response): Promise<T> {
  const json = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(extractUserMessage(json as ErrorBody));
  }
  if (json && typeof json === 'object' && 'data' in json) {
    return (json as { data: T }).data;
  }
  return json as T;
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  extraOptions?: RequestInit,
  isRetry = false
): Promise<T> {
  const token = getAccessToken();
  const url = `${BASE_URL}${path}`;

  const isFormData = extraOptions?.body instanceof FormData;
  const options: RequestInit = {
    method,
    headers: buildHeaders(token, !isFormData),
    credentials: 'include',
    ...extraOptions,
  };

  // If extraOptions provides headers (e.g. for FormData), merge them
  if (extraOptions?.headers) {
    options.headers = {
      ...buildHeaders(token, !isFormData),
      ...(extraOptions.headers as Record<string, string>),
    };
  }

  if (body !== undefined && !isFormData) {
    options.body = JSON.stringify(body);
  }

  const response = await fetchWithTimeout(url, options);

  if (response.status === 401 && !isRetry) {
    try {
      const data = await authService.refresh();
      setAccessToken(data.access_token);
      return request<T>(method, path, body, extraOptions, true);
    } catch {
      redirectToLogin();
      throw new Error('Sesión expirada. Por favor inicia sesión nuevamente.');
    }
  }

  return parseResponse<T>(response);
}

export const apiFetch = {
  get<T>(path: string, extraOptions?: RequestInit): Promise<T> {
    return request<T>('GET', path, undefined, extraOptions);
  },
  post<T>(path: string, body?: unknown, extraOptions?: RequestInit): Promise<T> {
    return request<T>('POST', path, body, extraOptions);
  },
  patch<T>(path: string, body?: unknown, extraOptions?: RequestInit): Promise<T> {
    return request<T>('PATCH', path, body, extraOptions);
  },
  delete<T>(path: string, extraOptions?: RequestInit): Promise<T> {
    return request<T>('DELETE', path, undefined, extraOptions);
  },
  /** For multipart/form-data — caller sets body as FormData, no Content-Type header */
  postForm<T>(path: string, formData: FormData): Promise<T> {
    return request<T>('POST', path, undefined, { body: formData });
  },
};
