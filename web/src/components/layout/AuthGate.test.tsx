import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import * as fc from 'fast-check';
import AuthGate from './AuthGate';
import { $isInitializing, $user } from '../../stores/authStore';

// ── Helpers ───────────────────────────────────────────────────────────────────

function renderAuthGate(children = <div>Protected</div>) {
  return render(
    <MemoryRouter initialEntries={['/']}>
      <Routes>
        <Route path="/" element={<AuthGate>{children}</AuthGate>} />
        <Route path="/login" element={<div>Login Page</div>} />
      </Routes>
    </MemoryRouter>
  );
}

// ── Setup ─────────────────────────────────────────────────────────────────────

beforeEach(() => {
  $isInitializing.set(false);
  $user.set(null);
  vi.clearAllMocks();
});

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('AuthGate', () => {
  it('renders spinner while $isInitializing is true', () => {
    $isInitializing.set(true);
    $user.set(null);
    renderAuthGate();
    expect(screen.getByRole('status')).toBeInTheDocument();
    expect(screen.queryByText('Protected')).not.toBeInTheDocument();
  });

  it('renders children when authenticated', () => {
    $user.set({ sub: 'u1', email: 'a@b.com', roles: [] });
    renderAuthGate();
    expect(screen.getByText('Protected')).toBeInTheDocument();
  });

  it('navigates to /login when not authenticated and not initializing', async () => {
    $user.set(null);
    $isInitializing.set(false);
    renderAuthGate();
    await waitFor(() => {
      expect(screen.getByText('Login Page')).toBeInTheDocument();
    });
    expect(screen.queryByText('Protected')).not.toBeInTheDocument();
  });

  it('does not navigate while still initializing', () => {
    $isInitializing.set(true);
    $user.set(null);
    renderAuthGate();
    expect(screen.queryByText('Login Page')).not.toBeInTheDocument();
    expect(screen.getByRole('status')).toBeInTheDocument();
  });
});

// Feature: profile-frontend, Property 13: Authentication Gate
describe('Property 13: Authentication Gate', () => {
  it('navigates to /login when not authenticated and not initializing', async () => {
    await fc.assert(
      fc.asyncProperty(fc.constant(null), async (_) => {
        $user.set(null);
        $isInitializing.set(false);
        const { unmount } = renderAuthGate(<div data-testid="protected">Content</div>);
        await waitFor(() => {
          const hasContent = document.querySelector('[data-testid="protected"]') !== null;
          expect(hasContent).toBe(false);
        });
        unmount();
      }),
      { numRuns: 5 }
    );
  });
});
