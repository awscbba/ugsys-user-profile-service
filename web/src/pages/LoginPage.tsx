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
    <div className="flex items-center justify-center min-h-screen bg-primary font-sans">
      <form
        onSubmit={handleSubmit}
        noValidate
        aria-label="Formulario de inicio de sesión"
        className="flex flex-col gap-4 p-10 bg-white rounded-xl shadow-lg w-[360px]"
      >
        <h1 className="m-0 text-[22px] font-bold text-gray-900">Mi Perfil</h1>

        {/* Error banner */}
        {error && (
          <p role="alert" className="m-0 text-[13px] text-red-600">
            {error}
          </p>
        )}

        <label className="flex flex-col gap-1 text-sm text-gray-700">
          Correo electrónico
          <input
            ref={emailRef}
            id="email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            disabled={isLoading}
            className="px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-accent disabled:bg-gray-50 disabled:text-gray-400"
          />
        </label>

        <label className="flex flex-col gap-1 text-sm text-gray-700">
          Contraseña
          <input
            id="password"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            disabled={isLoading}
            className="px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-accent disabled:bg-gray-50 disabled:text-gray-400"
          />
        </label>

        <button
          type="submit"
          disabled={isLoading}
          className="py-2.5 bg-brand hover:bg-brand/90 text-primary border-none rounded-md text-sm font-semibold cursor-pointer disabled:opacity-70 disabled:cursor-not-allowed transition-colors"
        >
          {isLoading ? 'Iniciando sesión…' : 'Iniciar sesión'}
        </button>
      </form>
    </div>
  );
}
