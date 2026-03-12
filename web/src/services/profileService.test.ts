import { describe, it, expect, beforeEach, vi } from 'vitest';

vi.mock('./httpClient', () => ({
  apiFetch: {
    get: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
    postForm: vi.fn(),
  },
}));

import { apiFetch } from './httpClient';
import { profileService } from './profileService';
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
  vi.clearAllMocks();
});

describe('profileService.getMe', () => {
  it('calls GET /api/v1/profiles/me', async () => {
    vi.mocked(apiFetch.get).mockResolvedValue(mockProfile);
    const result = await profileService.getMe();
    expect(apiFetch.get).toHaveBeenCalledWith('/api/v1/profiles/me');
    expect(result).toEqual(mockProfile);
  });
});

describe('profileService.updatePersonal', () => {
  it('calls PATCH /api/v1/profiles/{userId}/personal', async () => {
    vi.mocked(apiFetch.patch).mockResolvedValue(mockProfile);
    await profileService.updatePersonal('u1', {
      full_name: 'New Name',
      date_of_birth: '1990-01-01',
    });
    expect(apiFetch.patch).toHaveBeenCalledWith('/api/v1/profiles/u1/personal', {
      full_name: 'New Name',
      date_of_birth: '1990-01-01',
    });
  });
});

describe('profileService.updateContact', () => {
  it('calls PATCH /api/v1/profiles/{userId}/contact', async () => {
    vi.mocked(apiFetch.patch).mockResolvedValue(mockProfile);
    const body = { phone: '+591 70000001', address: mockProfile.address };
    await profileService.updateContact('u1', body);
    expect(apiFetch.patch).toHaveBeenCalledWith('/api/v1/profiles/u1/contact', body);
  });
});

describe('profileService.updateDisplay', () => {
  it('calls PATCH /api/v1/profiles/{userId}/display', async () => {
    vi.mocked(apiFetch.patch).mockResolvedValue(mockProfile);
    await profileService.updateDisplay('u1', { bio: 'Hello', display_name: 'Dev' });
    expect(apiFetch.patch).toHaveBeenCalledWith('/api/v1/profiles/u1/display', {
      bio: 'Hello',
      display_name: 'Dev',
    });
  });
});

describe('profileService.updatePreferences', () => {
  it('calls PATCH /api/v1/profiles/{userId}/preferences', async () => {
    vi.mocked(apiFetch.patch).mockResolvedValue(mockProfile);
    const body = {
      notification_preferences: { email: true, sms: false, whatsapp: false },
      language: 'en',
      timezone: 'UTC',
    };
    await profileService.updatePreferences('u1', body);
    expect(apiFetch.patch).toHaveBeenCalledWith('/api/v1/profiles/u1/preferences', body);
  });
});

describe('profileService.uploadAvatar', () => {
  it('calls postForm with FormData containing the file', async () => {
    vi.mocked(apiFetch.postForm).mockResolvedValue(mockProfile);
    const file = new File(['x'], 'photo.jpg', { type: 'image/jpeg' });
    await profileService.uploadAvatar('u1', file);
    expect(apiFetch.postForm).toHaveBeenCalledWith(
      '/api/v1/profiles/u1/avatar',
      expect.any(FormData)
    );
  });
});

describe('profileService.deleteAvatar', () => {
  it('calls DELETE /api/v1/profiles/{userId}/avatar', async () => {
    vi.mocked(apiFetch.delete).mockResolvedValue(undefined);
    await profileService.deleteAvatar('u1');
    expect(apiFetch.delete).toHaveBeenCalledWith('/api/v1/profiles/u1/avatar');
  });
});
