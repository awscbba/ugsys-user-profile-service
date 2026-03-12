import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import PreferencesSection from './PreferencesSection';
import { $profile } from '../../stores/profileStore';
import type { ProfileResponse } from '../../types/profile';

vi.mock('../../services/profileService', () => ({
  profileService: { updatePreferences: vi.fn() },
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

describe('PreferencesSection — read mode', () => {
  it('renders language and timezone', () => {
    render(<PreferencesSection />);
    expect(screen.getByText('es')).toBeInTheDocument();
    expect(screen.getByText('America/La_Paz')).toBeInTheDocument();
  });

  it('shows Editar button', () => {
    render(<PreferencesSection />);
    expect(screen.getByRole('button', { name: /editar/i })).toBeInTheDocument();
  });

  it('renders nothing when profile is null', () => {
    $profile.set(null);
    const { container } = render(<PreferencesSection />);
    expect(container.firstChild).toBeNull();
  });

  it('shows active notification channels', () => {
    render(<PreferencesSection />);
    // email is true in baseProfile
    expect(screen.getByText(/email/i)).toBeInTheDocument();
  });
});

describe('PreferencesSection — edit mode', () => {
  it('shows notification checkboxes, language and timezone selects', () => {
    render(<PreferencesSection />);
    fireEvent.click(screen.getByRole('button', { name: /editar/i }));
    expect(screen.getByLabelText(/idioma/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/zona horaria/i)).toBeInTheDocument();
    // 3 checkboxes for email, sms, whatsapp
    const checkboxes = screen.getAllByRole('checkbox');
    expect(checkboxes).toHaveLength(3);
  });

  it('shows Guardar and Cancelar buttons in edit mode', () => {
    render(<PreferencesSection />);
    fireEvent.click(screen.getByRole('button', { name: /editar/i }));
    expect(screen.getByRole('button', { name: /guardar/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /cancelar/i })).toBeInTheDocument();
  });

  it('Cancelar returns to read mode', () => {
    render(<PreferencesSection />);
    fireEvent.click(screen.getByRole('button', { name: /editar/i }));
    fireEvent.click(screen.getByRole('button', { name: /cancelar/i }));
    expect(screen.getByRole('button', { name: /editar/i })).toBeInTheDocument();
  });

  it('toggling a checkbox updates the draft', () => {
    render(<PreferencesSection />);
    fireEvent.click(screen.getByRole('button', { name: /editar/i }));
    const checkboxes = screen.getAllByRole('checkbox');
    // sms is index 1, starts unchecked
    expect(checkboxes[1]).not.toBeChecked();
    fireEvent.click(checkboxes[1]);
    expect(checkboxes[1]).toBeChecked();
  });

  it('changing language select updates draft', () => {
    render(<PreferencesSection />);
    fireEvent.click(screen.getByRole('button', { name: /editar/i }));
    const langSelect = screen.getByLabelText(/idioma/i);
    fireEvent.change(langSelect, { target: { value: 'en' } });
    expect((langSelect as HTMLSelectElement).value).toBe('en');
  });

  it('changing timezone select updates draft', () => {
    render(<PreferencesSection />);
    fireEvent.click(screen.getByRole('button', { name: /editar/i }));
    const tzSelect = screen.getByLabelText(/zona horaria/i);
    fireEvent.change(tzSelect, { target: { value: 'UTC' } });
    expect((tzSelect as HTMLSelectElement).value).toBe('UTC');
  });
});
