import { describe, it, expect, beforeEach, vi } from 'vitest';

vi.mock('../services/profileService', () => ({
  profileService: {
    getMe: vi.fn(),
  },
}));

vi.mock('../utils/toast', () => ({
  addToast: vi.fn(),
  $toasts: { get: vi.fn(() => []), set: vi.fn() },
}));

import { profileService } from '../services/profileService';
import { addToast } from '../utils/toast';
import { $profile, $profileLoading, $profileError, loadProfile } from './profileStore';
import type { ProfileResponse } from '../types/profile';

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
  $profileError.set(null);
  vi.clearAllMocks();
});

describe('loadProfile — success', () => {
  it('populates $profile and sets loading false', async () => {
    vi.mocked(profileService.getMe).mockResolvedValue(mockProfile);
    await loadProfile();
    expect($profile.get()).toEqual(mockProfile);
    expect($profileLoading.get()).toBe(false);
    expect($profileError.get()).toBeNull();
  });
});

describe('loadProfile — non-200 non-401 error', () => {
  it('adds a toast and keeps $profile null', async () => {
    vi.mocked(profileService.getMe).mockRejectedValue(new Error('Server error'));
    await loadProfile();
    expect($profile.get()).toBeNull();
    expect($profileLoading.get()).toBe(false);
    expect(addToast).toHaveBeenCalledOnce();
    // toast message must not contain status codes
    const toastMsg = vi.mocked(addToast).mock.calls[0][0];
    expect(toastMsg).not.toMatch(/\d{3}/);
  });
});
