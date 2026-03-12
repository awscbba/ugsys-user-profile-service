import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/react';
import * as fc from 'fast-check';
import AvatarUploader from './AvatarUploader';
import { $profile } from '../../stores/profileStore';
import { $toasts, addToast } from '../../utils/toast';
import type { ProfileResponse } from '../../types/profile';

vi.mock('../../services/profileService', () => ({
  profileService: {
    uploadAvatar: vi.fn(),
    deleteAvatar: vi.fn(),
  },
}));

vi.mock('../../utils/toast', () => ({
  addToast: vi.fn(),
  $toasts: { get: vi.fn(() => []), set: vi.fn() },
  dismissToast: vi.fn(),
}));

// URL.createObjectURL not available in jsdom
global.URL.createObjectURL = vi.fn(() => 'blob:preview-url');
global.URL.revokeObjectURL = vi.fn();

import { profileService } from '../../services/profileService';

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

function makeFile(name: string, type: string, size: number): File {
  const file = new File(['x'.repeat(Math.min(size, 100))], name, { type });
  Object.defineProperty(file, 'size', { value: size });
  return file;
}

beforeEach(() => {
  $profile.set({ ...baseProfile });
  vi.clearAllMocks();
});

describe('AvatarUploader — valid file', () => {
  it('shows preview and Confirm/Cancel buttons for valid file', () => {
    render(<AvatarUploader avatarUrl={null} userId="u1" />);
    const input = screen.getByTestId('avatar-input');
    const file = makeFile('photo.jpg', 'image/jpeg', 1024);
    fireEvent.change(input, { target: { files: [file] } });
    expect(screen.getByRole('button', { name: /confirmar/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /cancelar/i })).toBeInTheDocument();
  });

  it('handleClick triggers file input click', () => {
    render(<AvatarUploader avatarUrl={null} userId="u1" />);
    const input = screen.getByTestId('avatar-input');
    const clickSpy = vi.spyOn(input, 'click');
    fireEvent.click(screen.getByRole('button', { name: /cambiar foto/i }));
    expect(clickSpy).toHaveBeenCalledOnce();
  });

  it('handleCancel clears preview and hides Confirm/Cancel buttons', () => {
    render(<AvatarUploader avatarUrl={null} userId="u1" />);
    const input = screen.getByTestId('avatar-input');
    fireEvent.change(input, { target: { files: [makeFile('photo.jpg', 'image/jpeg', 1024)] } });
    expect(screen.getByRole('button', { name: /confirmar/i })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /cancelar/i }));
    expect(screen.queryByRole('button', { name: /confirmar/i })).not.toBeInTheDocument();
  });
});

describe('AvatarUploader — size rejection', () => {
  it('toasts and does not show preview for file > 5MB', () => {
    render(<AvatarUploader avatarUrl={null} userId="u1" />);
    const input = screen.getByTestId('avatar-input');
    const file = makeFile('big.jpg', 'image/jpeg', 6 * 1024 * 1024);
    fireEvent.change(input, { target: { files: [file] } });
    expect(addToast).toHaveBeenCalledWith(expect.stringContaining('5 MB'));
    expect(screen.queryByRole('button', { name: /confirmar/i })).not.toBeInTheDocument();
  });
});

describe('AvatarUploader — MIME rejection', () => {
  it('toasts and does not show preview for invalid MIME', () => {
    render(<AvatarUploader avatarUrl={null} userId="u1" />);
    const input = screen.getByTestId('avatar-input');
    const file = makeFile('doc.pdf', 'application/pdf', 1024);
    fireEvent.change(input, { target: { files: [file] } });
    expect(addToast).toHaveBeenCalledWith(expect.stringContaining('JPEG'));
    expect(screen.queryByRole('button', { name: /confirmar/i })).not.toBeInTheDocument();
  });
});

describe('AvatarUploader — upload success', () => {
  it('updates $profile.avatar_url on 200', async () => {
    const updatedProfile = { ...baseProfile, avatar_url: 'https://cdn.example.com/avatar.jpg' };
    vi.mocked(profileService.uploadAvatar).mockResolvedValue(updatedProfile);

    render(<AvatarUploader avatarUrl={null} userId="u1" />);
    const input = screen.getByTestId('avatar-input');
    fireEvent.change(input, { target: { files: [makeFile('photo.jpg', 'image/jpeg', 1024)] } });
    fireEvent.click(screen.getByRole('button', { name: /confirmar/i }));

    await waitFor(() => {
      expect($profile.get()?.avatar_url).toBe('https://cdn.example.com/avatar.jpg');
    });
  });
});

describe('AvatarUploader — upload error', () => {
  it('retains previous avatar_url on non-200', async () => {
    vi.mocked(profileService.uploadAvatar).mockRejectedValue(new Error('Error al subir'));
    $profile.set({ ...baseProfile, avatar_url: 'https://cdn.example.com/old.jpg' });

    render(<AvatarUploader avatarUrl="https://cdn.example.com/old.jpg" userId="u1" />);
    const input = screen.getByTestId('avatar-input');
    fireEvent.change(input, { target: { files: [makeFile('photo.jpg', 'image/jpeg', 1024)] } });
    fireEvent.click(screen.getByRole('button', { name: /confirmar/i }));

    await waitFor(() => {
      expect(addToast).toHaveBeenCalledOnce();
      expect($profile.get()?.avatar_url).toBe('https://cdn.example.com/old.jpg');
    });
  });
});

describe('AvatarUploader — delete', () => {
  it('sets avatar_url to null on successful delete', async () => {
    vi.mocked(profileService.deleteAvatar).mockResolvedValue(undefined);
    $profile.set({ ...baseProfile, avatar_url: 'https://cdn.example.com/avatar.jpg' });

    render(<AvatarUploader avatarUrl="https://cdn.example.com/avatar.jpg" userId="u1" />);
    fireEvent.click(screen.getByRole('button', { name: /eliminar foto/i }));

    await waitFor(() => {
      expect($profile.get()?.avatar_url).toBeNull();
    });
  });
});

// Feature: profile-frontend, Property 9: Invalid Avatar File Rejected Client-Side
describe('Property 9: Invalid Avatar File Rejected Client-Side', () => {
  it('rejects any file > 5MB or with invalid MIME — no fetch call, toast shown', () => {
    fc.assert(
      fc.property(
        fc.oneof(
          // oversized valid MIME
          fc.record({
            name: fc.constant('big.jpg'),
            type: fc.constant('image/jpeg'),
            size: fc.integer({ min: 5 * 1024 * 1024 + 1, max: 20 * 1024 * 1024 }),
          }),
          // valid size, invalid MIME
          fc.record({
            name: fc.constant('doc.pdf'),
            type: fc.constant('application/pdf'),
            size: fc.integer({ min: 1, max: 1024 }),
          })
        ),
        ({ name, type, size }) => {
          vi.clearAllMocks();
          $profile.set({ ...baseProfile });
          const { container } = render(<AvatarUploader avatarUrl={null} userId="u1" />);
          const input = container.querySelector('[data-testid="avatar-input"]') as HTMLInputElement;
          const file = makeFile(name, type, size);
          fireEvent.change(input, { target: { files: [file] } });
          expect(profileService.uploadAvatar).not.toHaveBeenCalled();
          expect(addToast).toHaveBeenCalled();
          cleanup();
        }
      ),
      { numRuns: 50 }
    );
  });
});
