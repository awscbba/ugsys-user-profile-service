import { useRef, useState } from 'react';
import { profileService } from '../../services/profileService';
import { $profile } from '../../stores/profileStore';
import { addToast } from '../../utils/toast';

const MAX_SIZE = 5 * 1024 * 1024; // 5 MB
const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/webp'];

interface AvatarUploaderProps {
  avatarUrl: string | null;
  userId: string;
}

export default function AvatarUploader({ avatarUrl, userId }: AvatarUploaderProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [pendingFile, setPendingFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  function handleClick() {
    inputRef.current?.click();
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    if (file.size > MAX_SIZE) {
      addToast('El archivo supera el límite de 5 MB');
      e.target.value = '';
      return;
    }

    if (!ALLOWED_TYPES.includes(file.type)) {
      addToast('Solo se aceptan imágenes JPEG, PNG o WebP');
      e.target.value = '';
      return;
    }

    setPreview(URL.createObjectURL(file));
    setPendingFile(file);
    e.target.value = '';
  }

  async function handleConfirm() {
    if (!pendingFile) return;
    setIsUploading(true);
    try {
      const response = await profileService.uploadAvatar(userId, pendingFile);
      const current = $profile.get();
      if (current) {
        $profile.set({ ...current, avatar_url: response.avatar_url });
      }
      if (preview) URL.revokeObjectURL(preview);
      setPreview(null);
      setPendingFile(null);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'No se pudo subir la imagen';
      addToast(message);
      if (preview) URL.revokeObjectURL(preview);
      setPreview(null);
      setPendingFile(null);
    } finally {
      setIsUploading(false);
    }
  }

  function handleCancel() {
    if (preview) URL.revokeObjectURL(preview);
    setPreview(null);
    setPendingFile(null);
  }

  async function handleDelete() {
    setIsDeleting(true);
    try {
      await profileService.deleteAvatar(userId);
      const current = $profile.get();
      if (current) {
        $profile.set({ ...current, avatar_url: null });
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'No se pudo eliminar la imagen';
      addToast(message);
    } finally {
      setIsDeleting(false);
    }
  }

  const displayUrl = preview ?? avatarUrl;

  return (
    <div className="flex flex-col items-center gap-4 p-6 bg-white rounded-lg shadow">
      <button
        type="button"
        onClick={handleClick}
        aria-label="Cambiar foto de perfil"
        className="relative w-24 h-24 rounded-full overflow-hidden border-2 border-brand focus:outline-none focus:ring-2 focus:ring-brand"
      >
        {displayUrl ? (
          <img src={displayUrl} alt="Avatar" className="w-full h-full object-cover" />
        ) : (
          <div
            className="w-full h-full bg-gray-200 flex items-center justify-center"
            aria-label="Avatar placeholder"
          >
            <svg
              aria-hidden="true"
              className="w-12 h-12 text-gray-400"
              fill="currentColor"
              viewBox="0 0 24 24"
            >
              <path d="M12 12c2.7 0 4.8-2.1 4.8-4.8S14.7 2.4 12 2.4 7.2 4.5 7.2 7.2 9.3 12 12 12zm0 2.4c-3.2 0-9.6 1.6-9.6 4.8v2.4h19.2v-2.4c0-3.2-6.4-4.8-9.6-4.8z" />
            </svg>
          </div>
        )}
      </button>

      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        onChange={handleFileChange}
        className="hidden"
        aria-label="Seleccionar imagen"
        data-testid="avatar-input"
      />

      {preview && (
        <div className="flex gap-3">
          <button
            type="button"
            onClick={handleConfirm}
            disabled={isUploading}
            className="px-4 py-2 bg-brand text-primary rounded text-sm font-medium disabled:opacity-50"
          >
            {isUploading ? 'Subiendo…' : 'Confirmar'}
          </button>
          <button
            type="button"
            onClick={handleCancel}
            disabled={isUploading}
            className="px-4 py-2 border border-gray-300 rounded text-sm font-medium text-gray-700"
          >
            Cancelar
          </button>
        </div>
      )}

      {!preview && avatarUrl && (
        <button
          type="button"
          onClick={handleDelete}
          disabled={isDeleting}
          className="text-sm text-red-600 hover:underline disabled:opacity-50"
        >
          {isDeleting ? 'Eliminando…' : 'Eliminar foto'}
        </button>
      )}
    </div>
  );
}
