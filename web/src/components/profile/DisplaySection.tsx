import { useStore } from '@nanostores/react';
import { $profile } from '../../stores/profileStore';
import { profileService } from '../../services/profileService';
import { useEditSection } from '../../hooks/useEditSection';
import type { UpdateDisplayRequest } from '../../types/profile';

const MAX_BIO = 500;

export default function DisplaySection() {
  const profile = useStore($profile);

  const currentValue: UpdateDisplayRequest = {
    bio: profile?.bio ?? null,
    display_name: profile?.display_name ?? null,
  };

  const {
    isEditing,
    isSaving,
    draft,
    setDraft,
    startEdit,
    cancelEdit,
    submitEdit,
    validationError,
  } = useEditSection<UpdateDisplayRequest>({
    currentValue,
    onSave: (value) => profileService.updateDisplay(profile!.user_id, value),
    validate: (v) =>
      v.bio !== null && v.bio.length > MAX_BIO
        ? `La biografía no puede superar ${MAX_BIO} caracteres`
        : null,
  });

  if (!profile) return null;

  const bioLength = draft.bio?.length ?? 0;
  const bioOverLimit = bioLength > MAX_BIO;

  return (
    <section className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-900">Información de Presentación</h2>
        {!isEditing && (
          <button
            type="button"
            onClick={startEdit}
            className="text-sm text-[#FF9900] hover:underline"
          >
            Editar
          </button>
        )}
      </div>

      {isEditing ? (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            submitEdit();
          }}
          className="space-y-4"
        >
          <div>
            <label htmlFor="display_name" className="block text-sm font-medium text-gray-700">
              Nombre de presentación
            </label>
            <input
              id="display_name"
              type="text"
              value={draft.display_name ?? ''}
              onChange={(e) => setDraft({ ...draft, display_name: e.target.value || null })}
              className="mt-1 block w-full rounded border-gray-300 shadow-sm sm:text-sm"
            />
          </div>
          <div>
            <label htmlFor="bio" className="block text-sm font-medium text-gray-700">
              Biografía
            </label>
            <textarea
              id="bio"
              rows={4}
              value={draft.bio ?? ''}
              onChange={(e) => setDraft({ ...draft, bio: e.target.value || null })}
              className="mt-1 block w-full rounded border-gray-300 shadow-sm sm:text-sm"
              aria-label="bio"
            />
            <p
              data-testid="bio-counter"
              className={`mt-1 text-xs ${bioOverLimit ? 'text-red-600' : 'text-gray-500'}`}
            >
              {MAX_BIO - bioLength}
            </p>
            {validationError && <p className="mt-1 text-sm text-red-600">{validationError}</p>}
          </div>
          <div className="flex gap-3">
            <button
              type="submit"
              disabled={isSaving || bioOverLimit}
              className="px-4 py-2 bg-[#FF9900] text-white rounded text-sm font-medium disabled:opacity-50"
            >
              {isSaving ? 'Guardando…' : 'Guardar'}
            </button>
            <button
              type="button"
              onClick={cancelEdit}
              disabled={isSaving}
              className="px-4 py-2 border border-gray-300 rounded text-sm font-medium text-gray-700"
            >
              Cancelar
            </button>
          </div>
        </form>
      ) : (
        <dl className="space-y-2">
          <div>
            <dt className="text-sm text-gray-500">Nombre de presentación</dt>
            <dd className="text-sm font-medium text-gray-900">{profile.display_name ?? '—'}</dd>
          </div>
          <div>
            <dt className="text-sm text-gray-500">Biografía</dt>
            <dd className="text-sm font-medium text-gray-900">{profile.bio ?? '—'}</dd>
          </div>
        </dl>
      )}
    </section>
  );
}
