import { useStore } from '@nanostores/react';
import { $profile } from '../../stores/profileStore';
import { profileService } from '../../services/profileService';
import { useEditSection } from '../../hooks/useEditSection';
import type { UpdatePreferencesRequest } from '../../types/profile';

const LANGUAGES = [
  { code: 'es', label: 'Español' },
  { code: 'en', label: 'English' },
  { code: 'pt', label: 'Português' },
];

const TIMEZONES = [
  'America/La_Paz',
  'America/Lima',
  'America/Bogota',
  'America/Santiago',
  'America/Buenos_Aires',
  'America/Sao_Paulo',
  'America/Mexico_City',
  'America/New_York',
  'America/Los_Angeles',
  'Europe/Madrid',
  'UTC',
];

export default function PreferencesSection() {
  const profile = useStore($profile);

  const currentValue: UpdatePreferencesRequest = {
    notification_preferences: profile?.notification_preferences
      ? { ...profile.notification_preferences }
      : { email: false, sms: false, whatsapp: false },
    language: profile?.language ?? 'es',
    timezone: profile?.timezone ?? 'America/La_Paz',
  };

  const { isEditing, isSaving, draft, setDraft, startEdit, cancelEdit, submitEdit } =
    useEditSection<UpdatePreferencesRequest>({
      currentValue,
      onSave: (value) => profileService.updatePreferences(profile!.user_id, value),
    });

  if (!profile) return null;

  return (
    <section className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-900">Preferencias</h2>
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
          <fieldset>
            <legend className="text-sm font-medium text-gray-700 mb-2">Notificaciones</legend>
            <div className="space-y-2">
              {(['email', 'sms', 'whatsapp'] as const).map((channel) => (
                <label key={channel} className="flex items-center gap-2 text-sm text-gray-700">
                  <input
                    type="checkbox"
                    checked={draft.notification_preferences[channel]}
                    onChange={(e) =>
                      setDraft({
                        ...draft,
                        notification_preferences: {
                          ...draft.notification_preferences,
                          [channel]: e.target.checked,
                        },
                      })
                    }
                  />
                  {channel.charAt(0).toUpperCase() + channel.slice(1)}
                </label>
              ))}
            </div>
          </fieldset>

          <div>
            <label htmlFor="language" className="block text-sm font-medium text-gray-700">
              Idioma
            </label>
            <select
              id="language"
              value={draft.language}
              onChange={(e) => setDraft({ ...draft, language: e.target.value })}
              className="mt-1 block w-full rounded border-gray-300 shadow-sm sm:text-sm"
            >
              {LANGUAGES.map(({ code, label }) => (
                <option key={code} value={code}>
                  {label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="timezone" className="block text-sm font-medium text-gray-700">
              Zona horaria
            </label>
            <select
              id="timezone"
              value={draft.timezone}
              onChange={(e) => setDraft({ ...draft, timezone: e.target.value })}
              className="mt-1 block w-full rounded border-gray-300 shadow-sm sm:text-sm"
            >
              {TIMEZONES.map((tz) => (
                <option key={tz} value={tz}>
                  {tz}
                </option>
              ))}
            </select>
          </div>

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
            <dt className="text-sm text-gray-500">Notificaciones</dt>
            <dd className="text-sm font-medium text-gray-900">
              {Object.entries(profile.notification_preferences)
                .filter(([, v]) => v)
                .map(([k]) => k)
                .join(', ') || 'Ninguna'}
            </dd>
          </div>
          <div>
            <dt className="text-sm text-gray-500">Idioma</dt>
            <dd className="text-sm font-medium text-gray-900">{profile.language}</dd>
          </div>
          <div>
            <dt className="text-sm text-gray-500">Zona horaria</dt>
            <dd className="text-sm font-medium text-gray-900">{profile.timezone}</dd>
          </div>
        </dl>
      )}
    </section>
  );
}
