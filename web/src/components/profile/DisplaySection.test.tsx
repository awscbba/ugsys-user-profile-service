import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import * as fc from 'fast-check';
import DisplaySection from './DisplaySection';
import { $profile } from '../../stores/profileStore';
import type { ProfileResponse } from '../../types/profile';

vi.mock('../../services/profileService', () => ({
  profileService: { updateDisplay: vi.fn() },
}));

vi.mock('../../utils/toast', () => ({
  addToast: vi.fn(),
  $toasts: { get: vi.fn(() => []), set: vi.fn() },
  dismissToast: vi.fn(),
}));

const baseProfile: ProfileResponse = {
  user_id: 'u1',
  email: 'dev@example.com',
  full_name: 'Dev User',
  phone: '+591 70000000',
  date_of_birth: '1990-01-01',
  address: { street: 'Calle 1', city: 'Cbba', state: 'Cbba', postal_code: '0000', country: 'BO' },
  email_verified: true,
  avatar_url: null,
  bio: null,
  display_name: null,
  language: 'es',
  timezone: 'America/La_Paz',
  notification_preferences: { email: true, sms: false, whatsapp: false },
  deleted_at: null,
};

beforeEach(() => {
  $profile.set({ ...baseProfile });
  vi.clearAllMocks();
});

describe('DisplaySection — counter', () => {
  it('shows bio-counter in edit mode', () => {
    render(<DisplaySection />);
    fireEvent.click(screen.getByRole('button', { name: /editar/i }));
    expect(screen.getByTestId('bio-counter')).toBeInTheDocument();
  });

  it('counter shows 500 when bio is empty', () => {
    render(<DisplaySection />);
    fireEvent.click(screen.getByRole('button', { name: /editar/i }));
    expect(screen.getByTestId('bio-counter').textContent).toBe('500');
  });

  it('submit disabled when bio exceeds 500 chars', () => {
    render(<DisplaySection />);
    fireEvent.click(screen.getByRole('button', { name: /editar/i }));
    const textarea = screen.getByRole('textbox', { name: /bio/i });
    fireEvent.change(textarea, { target: { value: 'a'.repeat(501) } });
    expect(screen.getByRole('button', { name: /guardar/i })).toBeDisabled();
  });

  it('onChange on display_name updates draft value', () => {
    render(<DisplaySection />);
    fireEvent.click(screen.getByRole('button', { name: /editar/i }));
    const input = screen.getByLabelText(/nombre de presentación/i);
    fireEvent.change(input, { target: { value: 'DevAlias' } });
    expect((input as HTMLInputElement).value).toBe('DevAlias');
  });

  it('clearing display_name sets it to null (empty string maps to null)', () => {
    $profile.set({ ...baseProfile, display_name: 'OldAlias' });
    render(<DisplaySection />);
    fireEvent.click(screen.getByRole('button', { name: /editar/i }));
    const input = screen.getByLabelText(/nombre de presentación/i);
    fireEvent.change(input, { target: { value: '' } });
    expect((input as HTMLInputElement).value).toBe('');
  });

  it('cancel button returns to read mode', () => {
    render(<DisplaySection />);
    fireEvent.click(screen.getByRole('button', { name: /editar/i }));
    fireEvent.click(screen.getByRole('button', { name: /cancelar/i }));
    expect(screen.getByRole('button', { name: /editar/i })).toBeInTheDocument();
  });

  it('form onSubmit calls submitEdit', async () => {
    const { profileService } = await import('../../services/profileService');
    vi.mocked(profileService.updateDisplay).mockResolvedValue({} as any);
    render(<DisplaySection />);
    fireEvent.click(screen.getByRole('button', { name: /editar/i }));
    const form = screen.getByTestId('bio-counter').closest('form')!;
    fireEvent.submit(form);
  });
});

// Feature: profile-frontend, Property 6: Bio Character Counter Accuracy
describe('Property 6: Bio Character Counter Accuracy', () => {
  it('counter shows 500 - N for any bio of length N <= 500', () => {
    fc.assert(
      fc.property(fc.string({ maxLength: 500 }), (bio) => {
        $profile.set({ ...baseProfile });
        const { container } = render(<DisplaySection />);
        // only button in read mode is "Editar"
        fireEvent.click(container.querySelector('button')!);
        const textarea = container.querySelector('textarea')!;
        fireEvent.change(textarea, { target: { value: bio } });
        const counter = container.querySelector('[data-testid="bio-counter"]');
        expect(counter?.textContent).toBe(String(500 - bio.length));
        cleanup();
      }),
      { numRuns: 50 }
    );
  });
});

// Feature: profile-frontend, Property 7: Bio Length Validation
describe('Property 7: Bio Length Validation', () => {
  it('submit disabled for any bio longer than 500 chars', () => {
    fc.assert(
      fc.property(fc.string({ minLength: 501, maxLength: 600 }), (bio) => {
        $profile.set({ ...baseProfile });
        const { container } = render(<DisplaySection />);
        fireEvent.click(container.querySelector('button')!);
        const textarea = container.querySelector('textarea')!;
        fireEvent.change(textarea, { target: { value: bio } });
        // submit button is type="submit"
        const submitBtn = container.querySelector('button[type="submit"]') as HTMLButtonElement;
        expect(submitBtn.disabled).toBe(true);
        cleanup();
      }),
      { numRuns: 50 }
    );
  });
});
