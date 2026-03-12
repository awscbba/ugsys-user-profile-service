import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import * as fc from 'fast-check';
import AuthGate from './AuthGate';
import { $isInitializing, $isAuthenticated } from '../../stores/authStore';

// $isAuthenticated is a computed — we drive it by setting $user
import { $user } from '../../stores/authStore';

beforeEach(() => {
  $isInitializing.set(false);
  $user.set(null);
  Object.defineProperty(window, 'location', { value: { href: '' }, writable: true });
  vi.clearAllMocks();
});

describe('AuthGate', () => {
  it('renders spinner while $isInitializing is true', () => {
    $isInitializing.set(true);
    render(
      <AuthGate>
        <div>Protected</div>
      </AuthGate>
    );
    expect(screen.getByRole('status')).toBeInTheDocument();
    expect(screen.queryByText('Protected')).not.toBeInTheDocument();
  });

  it('renders children when authenticated', () => {
    $user.set({ sub: 'u1', email: 'a@b.com', roles: [] });
    render(
      <AuthGate>
        <div>Protected</div>
      </AuthGate>
    );
    expect(screen.getByText('Protected')).toBeInTheDocument();
  });

  it('renders nothing when not authenticated and not initializing', () => {
    $user.set(null);
    $isInitializing.set(false);
    const { container } = render(
      <AuthGate>
        <div>Protected</div>
      </AuthGate>
    );
    expect(screen.queryByText('Protected')).not.toBeInTheDocument();
    expect(container.firstChild).toBeNull();
  });
});

// Feature: profile-frontend, Property 13: Authentication Gate
describe('Property 13: Authentication Gate', () => {
  it('renders no children when not authenticated and not initializing', () => {
    fc.assert(
      fc.property(fc.constant(null), (_) => {
        $user.set(null);
        $isInitializing.set(false);
        const { container } = render(
          <AuthGate>
            <div data-testid="protected">Content</div>
          </AuthGate>
        );
        const hasContent = container.querySelector('[data-testid="protected"]') !== null;
        expect(hasContent).toBe(false);
      }),
      { numRuns: 10 }
    );
  });
});
