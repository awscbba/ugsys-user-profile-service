import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ContactSection from './ContactSection';
import { $profile } from '../../stores/profileStore';
import type { ProfileResponse } from '../../types/profile';

vi.mock('../../services/profileService', () => ({
  profileService: { updateContact: vi.fn() },
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

describe('ContactSection — read mode', () => {
  it('renders phone and address', () => {
    render(<ContactSection />);
    expect(screen.getByText('+591 70000000')).toBeInTheDocument();
    expect(screen.getByText(/Calle 1/)).toBeInTheDocument();
  });

  it('shows Editar button', () => {
    render(<ContactSection />);
    expect(screen.getByRole('button', { name: /editar/i })).toBeInTheDocument();
  });

  it('renders nothing when profile is null', () => {
    $profile.set(null);
    const { container } = render(<ContactSection />);
    expect(container.firstChild).toBeNull();
  });
});

describe('ContactSection — edit mode', () => {
  it('shows phone and address inputs after clicking Editar', () => {
    render(<ContactSection />);
    fireEvent.click(screen.getByRole('button', { name: /editar/i }));
    expect(screen.getByLabelText(/teléfono/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/calle/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/ciudad/i)).toBeInTheDocument();
  });

  it('shows Guardar and Cancelar buttons in edit mode', () => {
    render(<ContactSection />);
    fireEvent.click(screen.getByRole('button', { name: /editar/i }));
    expect(screen.getByRole('button', { name: /guardar/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /cancelar/i })).toBeInTheDocument();
  });

  it('Cancelar returns to read mode', () => {
    render(<ContactSection />);
    fireEvent.click(screen.getByRole('button', { name: /editar/i }));
    fireEvent.click(screen.getByRole('button', { name: /cancelar/i }));
    expect(screen.getByRole('button', { name: /editar/i })).toBeInTheDocument();
  });

  it('updating phone input changes draft value', () => {
    render(<ContactSection />);
    fireEvent.click(screen.getByRole('button', { name: /editar/i }));
    const phoneInput = screen.getByLabelText(/teléfono/i);
    fireEvent.change(phoneInput, { target: { value: '+591 71111111' } });
    expect((phoneInput as HTMLInputElement).value).toBe('+591 71111111');
  });

  it('updating address fields changes draft values', () => {
    render(<ContactSection />);
    fireEvent.click(screen.getByRole('button', { name: /editar/i }));
    const cityInput = screen.getByLabelText(/ciudad/i);
    fireEvent.change(cityInput, { target: { value: 'La Paz' } });
    expect((cityInput as HTMLInputElement).value).toBe('La Paz');
  });
});
