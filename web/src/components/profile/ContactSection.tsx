import { useStore } from '@nanostores/react';
import { $profile } from '../../stores/profileStore';
import { profileService } from '../../services/profileService';
import { useEditSection } from '../../hooks/useEditSection';
import type { UpdateContactRequest } from '../../types/profile';

export default function ContactSection() {
  const profile = useStore($profile);
  if (!profile) return null;

  const currentValue: UpdateContactRequest = {
    phone: profile.phone,
    address: { ...profile.address },
  };

  const { isEditing, isSaving, draft, setDraft, startEdit, cancelEdit, submitEdit } =
    useEditSection<UpdateContactRequest>({
      currentValue,
      onSave: (value) => profileService.updateContact(profile.user_id, value),
    });

  return (
    <section className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-900">Información de Contacto</h2>
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
          {(
            [
              {
                id: 'phone',
                label: 'Teléfono',
                value: draft.phone,
                onChange: (v: string) => setDraft({ ...draft, phone: v }),
              },
            ] as { id: string; label: string; value: string; onChange: (v: string) => void }[]
          ).map(({ id, label, value, onChange }) => (
            <div key={id}>
              <label htmlFor={id} className="block text-sm font-medium text-gray-700">
                {label}
              </label>
              <input
                id={id}
                type="text"
                value={value}
                onChange={(e) => onChange(e.target.value)}
                className="mt-1 block w-full rounded border-gray-300 shadow-sm sm:text-sm"
              />
            </div>
          ))}
          {(
            [
              { id: 'street', label: 'Calle' },
              { id: 'city', label: 'Ciudad' },
              { id: 'state', label: 'Departamento' },
              { id: 'postal_code', label: 'Código postal' },
              { id: 'country', label: 'País' },
            ] as { id: keyof typeof draft.address; label: string }[]
          ).map(({ id, label }) => (
            <div key={id}>
              <label htmlFor={id} className="block text-sm font-medium text-gray-700">
                {label}
              </label>
              <input
                id={id}
                type="text"
                value={draft.address[id]}
                onChange={(e) =>
                  setDraft({ ...draft, address: { ...draft.address, [id]: e.target.value } })
                }
                className="mt-1 block w-full rounded border-gray-300 shadow-sm sm:text-sm"
              />
            </div>
          ))}
          <div className="flex gap-3">
            <button
              type="submit"
              disabled={isSaving}
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
            <dt className="text-sm text-gray-500">Teléfono</dt>
            <dd className="text-sm font-medium text-gray-900">{profile.phone}</dd>
          </div>
          <div>
            <dt className="text-sm text-gray-500">Dirección</dt>
            <dd className="text-sm font-medium text-gray-900">
              {profile.address.street}, {profile.address.city}, {profile.address.state}{' '}
              {profile.address.postal_code}, {profile.address.country}
            </dd>
          </div>
        </dl>
      )}
    </section>
  );
}
