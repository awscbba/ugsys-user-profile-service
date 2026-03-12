import { useStore } from '@nanostores/react';
import { $profile } from '../../stores/profileStore';
import { profileService } from '../../services/profileService';
import { useEditSection } from '../../hooks/useEditSection';
import type { UpdatePersonalRequest } from '../../types/profile';

export default function PersonalSection() {
  const profile = useStore($profile);

  const currentValue: UpdatePersonalRequest = {
    full_name: profile?.full_name ?? '',
    date_of_birth: profile?.date_of_birth ?? '',
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
  } = useEditSection<UpdatePersonalRequest>({
    currentValue,
    onSave: (value) => profileService.updatePersonal(profile!.user_id, value),
    validate: (v) => (v.full_name.trim().length === 0 ? 'El nombre no puede estar vacío' : null),
  });

  if (!profile) return null;

  return (
    <section className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-900">Información Personal</h2>
        {!isEditing && (
          <button type="button" onClick={startEdit} className="text-sm text-brand hover:underline">
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
            <label htmlFor="full_name" className="block text-sm font-medium text-gray-700">
              Nombre completo
            </label>
            <input
              id="full_name"
              type="text"
              value={draft.full_name}
              onChange={(e) => setDraft({ ...draft, full_name: e.target.value })}
              className="mt-1 block w-full rounded border-gray-300 shadow-sm focus:border-brand focus:ring-brand sm:text-sm"
            />
            {validationError && <p className="mt-1 text-sm text-red-600">{validationError}</p>}
          </div>
          <div>
            <label htmlFor="date_of_birth" className="block text-sm font-medium text-gray-700">
              Fecha de nacimiento
            </label>
            <input
              id="date_of_birth"
              type="date"
              value={draft.date_of_birth}
              onChange={(e) => setDraft({ ...draft, date_of_birth: e.target.value })}
              className="mt-1 block w-full rounded border-gray-300 shadow-sm focus:border-brand focus:ring-brand sm:text-sm"
            />
          </div>
          <div className="flex gap-3">
            <button
              type="submit"
              disabled={isSaving || draft.full_name.trim().length === 0}
              className="px-4 py-2 bg-brand text-primary rounded text-sm font-medium disabled:opacity-50"
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
            <dt className="text-sm text-gray-500">Nombre completo</dt>
            <dd className="text-sm font-medium text-gray-900">{profile.full_name}</dd>
          </div>
          <div>
            <dt className="text-sm text-gray-500">Fecha de nacimiento</dt>
            <dd className="text-sm font-medium text-gray-900">{profile.date_of_birth}</dd>
          </div>
        </dl>
      )}
    </section>
  );
}
