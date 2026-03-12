import { apiFetch } from './httpClient';
import type {
  ProfileResponse,
  UpdatePersonalRequest,
  UpdateContactRequest,
  UpdateDisplayRequest,
  UpdatePreferencesRequest,
} from '../types/profile';

export const profileService = {
  getMe(): Promise<ProfileResponse> {
    return apiFetch.get<ProfileResponse>('/api/v1/profiles/me');
  },

  updatePersonal(userId: string, body: UpdatePersonalRequest): Promise<ProfileResponse> {
    return apiFetch.patch<ProfileResponse>(`/api/v1/profiles/${userId}/personal`, body);
  },

  updateContact(userId: string, body: UpdateContactRequest): Promise<ProfileResponse> {
    return apiFetch.patch<ProfileResponse>(`/api/v1/profiles/${userId}/contact`, body);
  },

  updateDisplay(userId: string, body: UpdateDisplayRequest): Promise<ProfileResponse> {
    return apiFetch.patch<ProfileResponse>(`/api/v1/profiles/${userId}/display`, body);
  },

  updatePreferences(userId: string, body: UpdatePreferencesRequest): Promise<ProfileResponse> {
    return apiFetch.patch<ProfileResponse>(`/api/v1/profiles/${userId}/preferences`, body);
  },

  uploadAvatar(userId: string, file: File): Promise<ProfileResponse> {
    const formData = new FormData();
    formData.append('file', file);
    // postForm omits Content-Type so browser sets multipart boundary automatically
    return apiFetch.postForm<ProfileResponse>(`/api/v1/profiles/${userId}/avatar`, formData);
  },

  deleteAvatar(userId: string): Promise<void> {
    return apiFetch.delete<void>(`/api/v1/profiles/${userId}/avatar`);
  },
};
