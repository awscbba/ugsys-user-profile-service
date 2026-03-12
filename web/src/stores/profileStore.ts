import { atom } from 'nanostores';
import type { ProfileResponse } from '../types/profile';
import { profileService } from '../services/profileService';
import { addToast } from '../utils/toast';

export const $profile = atom<ProfileResponse | null>(null);
export const $profileLoading = atom<boolean>(false);
export const $profileError = atom<string | null>(null);

export async function loadProfile(): Promise<void> {
  $profileLoading.set(true);
  $profileError.set(null);
  try {
    const profile = await profileService.getMe();
    $profile.set(profile);
  } catch (err) {
    const message = err instanceof Error ? err.message : 'No se pudo cargar el perfil';
    $profileError.set(message);
    // 401 is handled by httpClient (redirects to login) — only toast for other errors
    addToast('No se pudo cargar el perfil. Intenta nuevamente.');
  } finally {
    $profileLoading.set(false);
  }
}
