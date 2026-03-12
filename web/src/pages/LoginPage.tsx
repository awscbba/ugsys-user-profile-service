/**
 * LoginPage — renders a login form that calls POST /api/v1/auth/login on the
 * identity-manager. On success, stores the access token and redirects to the
 * `redirect` query param (same origin only) or to `/`.
 */

import { useState, useRef, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { authService } from '../services/authService';
import { setAccessToken, $user } from '../stores/authStore';

function extractUser(token: string): { sub: string; email: string; roles: string[] } | null {
  try {
    const base64 = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
    const payload = JSON.parse(atob(base64)) as Record<string, unknown>;
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

/** Ensure redirect target is same-origin to prevent open redirect. */
function safeRedirect(raw: string | null): string {
  if (!raw) return '/';
  try {
    const url = new URL(raw, window.location.origin);
    if (url.origin !== window.location.origin) return '/';
    return url.pathname + url.search + url.hash;
  } catch {
    return '/';
  }
}

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const emailRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  useEffect(() => {
    emailRef.current?.focus();
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setIsLoading(true);
    try {
      const data = await authService.login(email, password);
      setAccessToken(data.access_token);
      const user = extractUser(data.access_token);
      $user.set(user);
      const redirectTo = safeRedirect(searchParams.get('redirect'));
      navigate(redirectTo, { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al iniciar sesión');
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-sm">
        {/* Header */}
        <div className="text-center mb-8">
          <p className="text-sm font-medium text-[#FF9900] uppercase tracking-wide">
            AWS User Group Cochabamba
          </p>
          <h1 className="mt-2 text-2xl font-bold text-gray-900">Iniciar sesión</h1>
        </div>

        {/* Card */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8">
          <form onSubmit={handleSubmit} noValidate aria-label="Formulario de inicio de sesión">
            {/* Error banner */}
            {error && (
              <div
                role="alert"
                className="mb-4 rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700"
              >
                {error}
              </div>
            )}

            {/* Email */}
            <div className="mb-4">
              <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
                Correo electrónico
              </label>
              <input
                ref={emailRef}
                id="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={isLoading}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-[#FF9900] focus:outline-none focus:ring-1 focus:ring-[#FF9900] disabled:bg-gray-50 disabled:text-gray-400"
                placeholder="tu@correo.com"
              />
            </div>

            {/* Password */}
            <div className="mb-6">
              <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
                Contraseña
              </label>
              <input
                id="password"
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={isLoading}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-[#FF9900] focus:outline-none focus:ring-1 focus:ring-[#FF9900] disabled:bg-gray-50 disabled:text-gray-400"
                placeholder="••••••••"
              />
            </div>

            {/* Submit */}
            <button
              type="submit"
              disabled={isLoading || !email || !password}
              className="w-full rounded-lg bg-[#FF9900] px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-[#e68a00] focus:outline-none focus:ring-2 focus:ring-[#FF9900] focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isLoading ? 'Iniciando sesión…' : 'Iniciar sesión'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
