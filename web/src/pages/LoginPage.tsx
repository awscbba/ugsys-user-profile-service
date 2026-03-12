/**
 * LoginPage — delegates all rendering to LoginCard from @ugsys/ui-lib.
 * Only owns: auth logic, redirect handling, state.
 */

import { useState, useRef, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { LoginCard } from '@ugsys/ui-lib';
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
    <LoginCard
      title="Mi Perfil"
      emailLabel="Correo electrónico"
      passwordLabel="Contraseña"
      submitLabel="Iniciar sesión"
      loadingLabel="Iniciando sesión…"
      email={email}
      password={password}
      isLoading={isLoading}
      error={error}
      onEmailChange={setEmail}
      onPasswordChange={setPassword}
      onSubmit={handleSubmit}
    />
  );
}
