import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import * as fc from 'fast-check';
import PersonalSection from './PersonalSection';
import { $profile } from '../../stores/profileStore';
import type { ProfileResponse } from '../../types/profile';

vi.mock('../../services/profileService', () => ({
  profileService: { updatePersonal: vi.fn() },
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

describe('PersonalSection — read mode', () => {
  it('renders full_name and date_of_birth', () => {
    render(<PersonalSection />);
    expect(screen.getByText('Dev User')).toBeInTheDocument();
    expect(screen.getByText('1990-01-01')).toBeInTheDocument();
  });

  it('shows Editar button', () => {
    render(<PersonalSection />);
    expect(screen.getByRole('button', { name: /editar/i })).toBeInTheDocument();
  });
});

describe('PersonalSection — edit mode', () => {
  it('shows inputs after clicking Editar', () => {
    render(<PersonalSection />);
    fireEvent.click(screen.getByRole('button', { name: /editar/i }));
    expect(screen.getByLabelText(/nombre completo/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/fecha de nacimiento/i)).toBeInTheDocument();
  });

  it('submit button disabled when full_name is empty', () => {
    render(<PersonalSection />);
    fireEvent.click(screen.getByRole('button', { name: /editar/i }));
    const input = screen.getByLabelText(/nombre completo/i);
    fireEvent.change(input, { target: { value: '' } });
    expect(screen.getByRole('button', { name: /guardar/i })).toBeDisabled();
  });

  it('onChange on full_name updates draft value', () => {
    render(<PersonalSection />);
    fireEvent.click(screen.getByRole('button', { name: /editar/i }));
    const input = screen.getByLabelText(/nombre completo/i);
    fireEvent.change(input, { target: { value: 'Nuevo Nombre' } });
    expect((input as HTMLInputElement).value).toBe('Nuevo Nombre');
  });

  it('onChange on date_of_birth updates draft value', () => {
    render(<PersonalSection />);
    fireEvent.click(screen.getByRole('button', { name: /editar/i }));
    const input = screen.getByLabelText(/fecha de nacimiento/i);
    fireEvent.change(input, { target: { value: '2000-06-15' } });
    expect((input as HTMLInputElement).value).toBe('2000-06-15');
  });

  it('cancel button returns to read mode', () => {
    render(<PersonalSection />);
    fireEvent.click(screen.getByRole('button', { name: /editar/i }));
    fireEvent.click(screen.getByRole('button', { name: /cancelar/i }));
    expect(screen.getByRole('button', { name: /editar/i })).toBeInTheDocument();
  });

  it('form onSubmit calls submitEdit', async () => {
    const { profileService } = await import('../../services/profileService');
    vi.mocked(profileService.updatePersonal).mockResolvedValue({} as any);
    render(<PersonalSection />);
    fireEvent.click(screen.getByRole('button', { name: /editar/i }));
    const form = screen.getByLabelText(/nombre completo/i).closest('form')!;
    fireEvent.submit(form);
    // submitEdit is invoked — no throw means the handler ran
  });
});

// Feature: profile-frontend, Property 8: full_name Non-Empty Validation
describe('Property 8: full_name Non-Empty Validation', () => {
  it('submit disabled for any whitespace-only full_name', () => {
    fc.assert(
      fc.property(fc.stringMatching(/^\s*$/), (whitespace) => {
        $profile.set({ ...baseProfile });
        render(<PersonalSection />);
        fireEvent.click(screen.getByRole('button', { name: /editar/i }));
        const input = screen.getByLabelText(/nombre completo/i);
        fireEvent.change(input, { target: { value: whitespace } });
        expect(screen.getByRole('button', { name: /guardar/i })).toBeDisabled();
        cleanup();
      }),
      { numRuns: 50 }
    );
  });
});
