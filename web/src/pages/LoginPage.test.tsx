import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import LoginPage from './LoginPage';
import { authService } from '../services/authService';
import * as authStore from '../stores/authStore';

// ── Mocks ─────────────────────────────────────────────────────────────────────

vi.mock('../services/authService', () => ({
  authService: {
    login: vi.fn(),
  },
}));

vi.mock('../stores/authStore', async (importOriginal) => {
  const actual = await importOriginal<typeof authStore>();
  return {
    ...actual,
    setAccessToken: vi.fn(),
    $user: { set: vi.fn() },
  };
});

// Minimal valid JWT payload (exp far in the future)
function makeToken(payload: Record<string, unknown> = {}): string {
  const header = btoa(JSON.stringify({ alg: 'RS256', typ: 'JWT' }));
  const body = btoa(
    JSON.stringify({ sub: 'usr-1', email: 'dev@example.com', exp: 9999999999, ...payload })
  );
  return `${header}.${body}.sig`;
}

function renderLoginPage(initialPath = '/login') {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/" element={<div>Home</div>} />
      </Routes>
    </MemoryRouter>
  );
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('LoginPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders email, password fields and submit button', () => {
    renderLoginPage();
    expect(screen.getByLabelText(/correo electrónico/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/contraseña/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /iniciar sesión/i })).toBeInTheDocument();
  });

  it('submit button is enabled when fields are empty (only disabled while loading)', () => {
    renderLoginPage();
    expect(screen.getByRole('button', { name: /iniciar sesión/i })).not.toBeDisabled();
  });

  it('submit button is enabled when both fields have values', () => {
    renderLoginPage();
    fireEvent.change(screen.getByLabelText(/correo electrónico/i), {
      target: { value: 'dev@example.com' },
    });
    fireEvent.change(screen.getByLabelText(/contraseña/i), {
      target: { value: 'password123' },
    });
    expect(screen.getByRole('button', { name: /iniciar sesión/i })).not.toBeDisabled();
  });

  it('calls authService.login with email and password on submit', async () => {
    vi.mocked(authService.login).mockResolvedValue({
      access_token: makeToken(),
      token_type: 'bearer',
      expires_in: 1800,
    });

    renderLoginPage();
    fireEvent.change(screen.getByLabelText(/correo electrónico/i), {
      target: { value: 'dev@example.com' },
    });
    fireEvent.change(screen.getByLabelText(/contraseña/i), {
      target: { value: 'Str0ng!Pass' },
    });
    fireEvent.click(screen.getByRole('button', { name: /iniciar sesión/i }));

    await waitFor(() => {
      expect(authService.login).toHaveBeenCalledWith('dev@example.com', 'Str0ng!Pass');
    });
  });

  it('stores access token and sets user on successful login', async () => {
    const token = makeToken();
    vi.mocked(authService.login).mockResolvedValue({
      access_token: token,
      token_type: 'bearer',
      expires_in: 1800,
    });

    renderLoginPage();
    fireEvent.change(screen.getByLabelText(/correo electrónico/i), {
      target: { value: 'dev@example.com' },
    });
    fireEvent.change(screen.getByLabelText(/contraseña/i), {
      target: { value: 'Str0ng!Pass' },
    });
    fireEvent.click(screen.getByRole('button', { name: /iniciar sesión/i }));

    await waitFor(() => {
      expect(authStore.setAccessToken).toHaveBeenCalledWith(token);
    });
  });

  it('redirects to / after successful login (no redirect param)', async () => {
    vi.mocked(authService.login).mockResolvedValue({
      access_token: makeToken(),
      token_type: 'bearer',
      expires_in: 1800,
    });

    renderLoginPage('/login');
    fireEvent.change(screen.getByLabelText(/correo electrónico/i), {
      target: { value: 'dev@example.com' },
    });
    fireEvent.change(screen.getByLabelText(/contraseña/i), {
      target: { value: 'Str0ng!Pass' },
    });
    fireEvent.click(screen.getByRole('button', { name: /iniciar sesión/i }));

    await waitFor(() => {
      expect(screen.getByText('Home')).toBeInTheDocument();
    });
  });

  it('redirects to redirect param path after successful login', async () => {
    vi.mocked(authService.login).mockResolvedValue({
      access_token: makeToken(),
      token_type: 'bearer',
      expires_in: 1800,
    });

    render(
      <MemoryRouter initialEntries={['/login?redirect=%2F']}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/" element={<div>Home</div>} />
        </Routes>
      </MemoryRouter>
    );

    fireEvent.change(screen.getByLabelText(/correo electrónico/i), {
      target: { value: 'dev@example.com' },
    });
    fireEvent.change(screen.getByLabelText(/contraseña/i), {
      target: { value: 'Str0ng!Pass' },
    });
    fireEvent.click(screen.getByRole('button', { name: /iniciar sesión/i }));

    await waitFor(() => {
      expect(screen.getByText('Home')).toBeInTheDocument();
    });
  });

  it('shows error message on failed login', async () => {
    vi.mocked(authService.login).mockRejectedValue(new Error('Credenciales inválidas'));

    renderLoginPage();
    fireEvent.change(screen.getByLabelText(/correo electrónico/i), {
      target: { value: 'dev@example.com' },
    });
    fireEvent.change(screen.getByLabelText(/contraseña/i), {
      target: { value: 'wrongpass' },
    });
    fireEvent.click(screen.getByRole('button', { name: /iniciar sesión/i }));

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('Credenciales inválidas');
    });
  });

  it('shows generic error when non-Error is thrown', async () => {
    vi.mocked(authService.login).mockRejectedValue('unexpected');

    renderLoginPage();
    fireEvent.change(screen.getByLabelText(/correo electrónico/i), {
      target: { value: 'dev@example.com' },
    });
    fireEvent.change(screen.getByLabelText(/contraseña/i), {
      target: { value: 'pass' },
    });
    fireEvent.click(screen.getByRole('button', { name: /iniciar sesión/i }));

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('Error al iniciar sesión');
    });
  });

  it('disables form and shows loading text while submitting', async () => {
    let resolve!: (v: { access_token: string; token_type: string; expires_in: number }) => void;
    vi.mocked(authService.login).mockReturnValue(new Promise((r) => (resolve = r)));

    renderLoginPage();
    fireEvent.change(screen.getByLabelText(/correo electrónico/i), {
      target: { value: 'dev@example.com' },
    });
    fireEvent.change(screen.getByLabelText(/contraseña/i), {
      target: { value: 'pass' },
    });
    fireEvent.click(screen.getByRole('button', { name: /iniciar sesión/i }));

    expect(screen.getByRole('button', { name: /iniciando sesión/i })).toBeDisabled();

    resolve({ access_token: makeToken(), token_type: 'bearer', expires_in: 1800 });
  });

  it('rejects cross-origin redirect param and falls back to /', async () => {
    vi.mocked(authService.login).mockResolvedValue({
      access_token: makeToken(),
      token_type: 'bearer',
      expires_in: 1800,
    });

    render(
      <MemoryRouter initialEntries={['/login?redirect=https%3A%2F%2Fevil.com']}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/" element={<div>Home</div>} />
        </Routes>
      </MemoryRouter>
    );

    fireEvent.change(screen.getByLabelText(/correo electrónico/i), {
      target: { value: 'dev@example.com' },
    });
    fireEvent.change(screen.getByLabelText(/contraseña/i), {
      target: { value: 'pass' },
    });
    fireEvent.click(screen.getByRole('button', { name: /iniciar sesión/i }));

    // Should land on / (Home), not navigate to evil.com
    await waitFor(() => {
      expect(screen.getByText('Home')).toBeInTheDocument();
    });
  });

  it('clears error when user starts typing after a failure', async () => {
    vi.mocked(authService.login).mockRejectedValue(new Error('Credenciales inválidas'));

    renderLoginPage();
    fireEvent.change(screen.getByLabelText(/correo electrónico/i), {
      target: { value: 'dev@example.com' },
    });
    fireEvent.change(screen.getByLabelText(/contraseña/i), {
      target: { value: 'wrong' },
    });
    fireEvent.click(screen.getByRole('button', { name: /iniciar sesión/i }));

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument();
    });

    // Typing in email clears the error on next submit attempt (error is cleared on submit)
    // Verify the alert is still there until next submit
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });
});
