import { useState } from 'react';
import type { ProfileResponse } from '../types/profile';
import { $profile } from '../stores/profileStore';
import { addToast } from '../utils/toast';

export interface UseEditSectionOptions<T> {
  currentValue: T;
  onSave: (value: T) => Promise<ProfileResponse>;
  validate?: (value: T) => string | null;
}

export interface UseEditSectionResult<T> {
  isEditing: boolean;
  isSaving: boolean;
  draft: T;
  setDraft: (v: T) => void;
  startEdit: () => void;
  cancelEdit: () => void;
  submitEdit: () => Promise<void>;
  validationError: string | null;
}

export function useEditSection<T>({
  currentValue,
  onSave,
  validate,
}: UseEditSectionOptions<T>): UseEditSectionResult<T> {
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [draft, setDraft] = useState<T>(currentValue);
  const [validationError, setValidationError] = useState<string | null>(null);

  function startEdit() {
    setDraft(currentValue);
    setValidationError(null);
    setIsEditing(true);
  }

  function cancelEdit() {
    setIsEditing(false);
    setDraft(currentValue);
    setValidationError(null);
  }

  async function submitEdit() {
    if (validate) {
      const error = validate(draft);
      if (error) {
        setValidationError(error);
        return;
      }
    }
    setValidationError(null);

    const snapshot = $profile.get();
    // Optimistic update — apply draft to store immediately
    if (snapshot) {
      $profile.set({ ...snapshot, ...(draft as Partial<ProfileResponse>) });
    }

    setIsSaving(true);
    try {
      const response = await onSave(draft);
      $profile.set(response);
      setIsEditing(false);
    } catch (err) {
      // Revert to snapshot on error
      $profile.set(snapshot);
      const message = err instanceof Error ? err.message : 'No se pudo guardar los cambios';
      addToast(message);
    } finally {
      setIsSaving(false);
    }
  }

  return {
    isEditing,
    isSaving,
    draft,
    setDraft,
    startEdit,
    cancelEdit,
    submitEdit,
    validationError,
  };
}
