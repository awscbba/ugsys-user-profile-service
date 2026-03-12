import { useStore } from '@nanostores/react';
import { $toasts, dismissToast } from '../../utils/toast';

export function ToastContainer() {
  const toasts = useStore($toasts);

  if (toasts.length === 0) return null;

  return (
    <div
      aria-live="polite"
      aria-label="Notificaciones"
      className="fixed bottom-4 right-4 z-50 flex flex-col gap-2"
    >
      {toasts.map((toast) => (
        <div
          key={toast.id}
          role="alert"
          className={`flex items-start gap-3 px-4 py-3 rounded-lg shadow-lg text-sm text-white max-w-sm ${
            toast.type === 'error'
              ? 'bg-red-600'
              : toast.type === 'success'
                ? 'bg-green-600'
                : 'bg-gray-700'
          }`}
        >
          <span className="flex-1">{toast.message}</span>
          <button
            type="button"
            onClick={() => dismissToast(toast.id)}
            aria-label="Cerrar notificación"
            className="flex-shrink-0 text-white/80 hover:text-white"
          >
            ✕
          </button>
        </div>
      ))}
    </div>
  );
}
