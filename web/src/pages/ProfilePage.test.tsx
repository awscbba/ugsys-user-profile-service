import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import ProfilePage from './ProfilePage';
import { $profile, $profileLoading } from '../stores/profileStore';
import type { ProfileResponse } from '../types/profile';

vi.mock('../stores/profileStore', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../stores/profileStore')>();
  return {
    ...actual,
    loadProfile: vi.fn(),
  };
});

vi.mock('../components/profile/AvatarUploader', () => ({
  default: ({ avatarUrl }: { avatarUrl: string | null }) => (
    <div data-testid="avatar-uploader">{avatarUrl ?? 'placeholder'}</div>
  ),
}));
vi.mock('../components/profile/PersonalSection', () => ({
  default: () => <div data-testid="personal-section" />,
}));
vi.mock('../components/profile/ContactSection', () => ({
  default: () => <div data-testid="contact-section" />,
}));
vi.mock('../components/profile/DisplaySection', () => ({
  default: () => <div data-testid="display-section" />,
}));
vi.mock('../components/profile/PreferencesSection', () => ({
  default: () => <div data-testid="preferences-section" />,
}));

const mockProfile: ProfileResponse = {
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
  $profile.set(null);
  $profileLoading.set(false);
  vi.clearAllMocks();
});

describe('ProfilePage', () => {
  it('shows skeleton while loading', () => {
    $profileLoading.set(true);
    render(<ProfilePage />);
    expect(screen.getByLabelText('Cargando perfil')).toBeInTheDocument();
  });

  it('renders all section components after profile loads', async () => {
    $profile.set(mockProfile);
    render(<ProfilePage />);
    await waitFor(() => {
      expect(screen.getByTestId('avatar-uploader')).toBeInTheDocument();
      expect(screen.getByTestId('personal-section')).toBeInTheDocument();
      expect(screen.getByTestId('contact-section')).toBeInTheDocument();
      expect(screen.getByTestId('display-section')).toBeInTheDocument();
      expect(screen.getByTestId('preferences-section')).toBeInTheDocument();
    });
  });

  it('uses full_name as primary name when display_name is null', async () => {
    $profile.set({ ...mockProfile, display_name: null });
    render(<ProfilePage />);
    await waitFor(() => {
      expect(screen.getByText('Dev User')).toBeInTheDocument();
    });
  });

  it('uses display_name as primary name when set', async () => {
    $profile.set({ ...mockProfile, display_name: 'DevAlias' });
    render(<ProfilePage />);
    await waitFor(() => {
      expect(screen.getByText('DevAlias')).toBeInTheDocument();
    });
  });

  it('shows placeholder when avatar_url is null', async () => {
    $profile.set({ ...mockProfile, avatar_url: null });
    render(<ProfilePage />);
    await waitFor(() => {
      expect(screen.getByText('placeholder')).toBeInTheDocument();
    });
  });
});
