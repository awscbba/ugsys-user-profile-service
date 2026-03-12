import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook, act, cleanup } from '@testing-library/react';
import * as fc from 'fast-check';
import { useEditSection } from './useEditSection';
import { $profile } from '../stores/profileStore';
import { addToast } from '../utils/toast';
import type { ProfileResponse } from '../types/profile';

vi.mock('../utils/toast', () => ({
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

type PersonalDraft = { full_name: string; date_of_birth: string };

/** Render the hook and flush the initial React 19 concurrent render. */
async function setup<T>(options: Parameters<typeof useEditSection<T>>[0]) {
  const hook = renderHook(() => useEditSection<T>(options));
  // React 19 defers the initial render — flush it before accessing result.current
  await act(async () => {});
  return hook;
}

beforeEach(() => {
  $profile.set({ ...baseProfile });
  vi.clearAllMocks();
});

describe('useEditSection — validation', () => {
  it('validation error blocks API call', async () => {
    const onSave = vi.fn().mockResolvedValue(baseProfile);
    const { result } = await setup<PersonalDraft>({
      currentValue: { full_name: '', date_of_birth: '1990-01-01' },
      onSave,
      validate: (v) => (v.full_name.trim().length === 0 ? 'Nombre requerido' : null),
    });

    await act(async () => result.current.startEdit());
    await act(async () => result.current.submitEdit());

    expect(result.current.validationError).toBe('Nombre requerido');
    expect(onSave).not.toHaveBeenCalled();
  });
});

describe('useEditSection — isSaving guard', () => {
  it('isSaving is true while in-flight', async () => {
    let resolveSave!: (v: ProfileResponse) => void;
    const onSave = vi.fn(
      () =>
        new Promise<ProfileResponse>((res) => {
          resolveSave = res;
        })
    );
    const { result } = await setup<PersonalDraft>({
      currentValue: { full_name: 'Dev', date_of_birth: '1990-01-01' },
      onSave,
    });

    await act(async () => result.current.startEdit());

    // Kick off submit without awaiting so we can inspect mid-flight state
    // We use a raw Promise here to avoid act() flushing the entire async chain
    let submitResolve!: () => void;
    const submitDonePromise = new Promise<void>((r) => {
      submitResolve = r;
    });
    act(() => {
      result.current.submitEdit().then(submitResolve);
    });

    // At this point submitEdit has been called but the onSave promise hasn't resolved
    expect(result.current.isSaving).toBe(true);

    // Now resolve and flush
    await act(async () => resolveSave(baseProfile));
    await submitDonePromise;
    expect(result.current.isSaving).toBe(false);
  });
});

describe('useEditSection — cancelEdit', () => {
  it('cancelEdit discards draft and exits edit mode', async () => {
    const { result } = await setup<PersonalDraft>({
      currentValue: { full_name: 'Dev', date_of_birth: '1990-01-01' },
      onSave: vi.fn(),
    });

    await act(async () => result.current.startEdit());
    await act(async () =>
      result.current.setDraft({ full_name: 'Changed', date_of_birth: '2000-01-01' })
    );
    await act(async () => result.current.cancelEdit());

    expect(result.current.isEditing).toBe(false);
    expect(result.current.draft.full_name).toBe('Dev');
  });
});

describe('useEditSection — revert on error', () => {
  it('reverts $profile to snapshot when onSave rejects', async () => {
    const snapshot = { ...baseProfile };
    $profile.set(snapshot);
    const onSave = vi.fn().mockRejectedValue(new Error('Server error'));

    const { result } = await setup<PersonalDraft>({
      currentValue: { full_name: 'Dev', date_of_birth: '1990-01-01' },
      onSave,
    });

    await act(async () => result.current.startEdit());
    await act(async () =>
      result.current.setDraft({ full_name: 'New Name', date_of_birth: '1990-01-01' })
    );
    await act(async () => result.current.submitEdit());

    expect($profile.get()?.full_name).toBe(snapshot.full_name);
    expect(addToast).toHaveBeenCalledOnce();
  });
});

// Feature: profile-frontend, Property 3: Optimistic Update Applied Immediately
describe('Property 3: Optimistic Update Applied Immediately', () => {
  it('$profile reflects draft synchronously before PATCH resolves', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.record({
          full_name: fc.string({ minLength: 1, maxLength: 50 }),
          date_of_birth: fc.constant('1990-01-01'),
        }),
        async (draft) => {
          $profile.set({ ...baseProfile });
          vi.clearAllMocks();

          let capturedOptimistic: ProfileResponse | null = null;
          let resolveOnSave!: (v: ProfileResponse) => void;
          const onSave = vi.fn(
            () =>
              new Promise<ProfileResponse>((res) => {
                capturedOptimistic = $profile.get();
                resolveOnSave = res;
              })
          );

          const { result } = renderHook(() =>
            useEditSection<PersonalDraft>({ currentValue: draft, onSave })
          );
          await act(async () => {});

          await act(async () => result.current.startEdit());

          let submitResolve!: () => void;
          const submitDone = new Promise<void>((r) => {
            submitResolve = r;
          });
          act(() => {
            result.current.submitEdit().then(submitResolve);
          });

          expect(capturedOptimistic?.full_name).toBe(draft.full_name);

          await act(async () => resolveOnSave({ ...baseProfile, ...draft }));
          await submitDone;
          cleanup();
        }
      ),
      { numRuns: 20 }
    );
  });
});

// Feature: profile-frontend, Property 4: Successful-Update Consistency
describe('Property 4: Successful-Update Consistency', () => {
  it('$profile equals submitted draft after 200 response', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.record({
          full_name: fc.string({ minLength: 1, maxLength: 50 }),
          date_of_birth: fc.constant('1990-01-01'),
        }),
        async (draft) => {
          $profile.set({ ...baseProfile });
          vi.clearAllMocks();

          const serverResponse = { ...baseProfile, ...draft };
          const onSave = vi.fn().mockResolvedValue(serverResponse);

          const { result } = renderHook(() =>
            useEditSection<PersonalDraft>({ currentValue: draft, onSave })
          );
          await act(async () => {});

          await act(async () => result.current.startEdit());
          await act(async () => result.current.submitEdit());

          expect($profile.get()?.full_name).toBe(draft.full_name);
          cleanup();
        }
      ),
      { numRuns: 20 }
    );
  });
});

// Feature: profile-frontend, Property 5: Revert-on-Error
describe('Property 5: Revert-on-Error', () => {
  it('$profile equals pre-edit snapshot after any non-200 PATCH', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.record({
          full_name: fc.string({ minLength: 1, maxLength: 50 }),
          date_of_birth: fc.constant('1990-01-01'),
        }),
        fc.integer({ min: 400, max: 599 }),
        async (draft, _errorStatus) => {
          const snapshot = { ...baseProfile };
          $profile.set(snapshot);
          vi.clearAllMocks();

          const onSave = vi.fn().mockRejectedValue(new Error('Error del servidor'));

          const { result } = renderHook(() =>
            useEditSection<PersonalDraft>({ currentValue: draft, onSave })
          );
          await act(async () => {});

          await act(async () => result.current.startEdit());
          await act(async () => result.current.submitEdit());

          expect($profile.get()?.full_name).toBe(snapshot.full_name);
          cleanup();
        }
      ),
      { numRuns: 20 }
    );
  });
});
