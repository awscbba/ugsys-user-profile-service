import { atom } from 'nanostores';

export interface Toast {
  id: string;
  message: string;
  type: 'error' | 'success' | 'info';
}

export const $toasts = atom<Toast[]>([]);

export function addToast(message: string, type: Toast['type'] = 'error'): void {
  const current = $toasts.get();
  if (current.length >= 3) return; // cap at 3; auto-dismiss frees slots
  const id = crypto.randomUUID();
  $toasts.set([...current, { id, message, type }]);
  setTimeout(() => dismissToast(id), 5_000);
}

export function dismissToast(id: string): void {
  $toasts.set($toasts.get().filter((t) => t.id !== id));
}
