import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import * as fc from 'fast-check';
import { $toasts, addToast, dismissToast } from './toast';

beforeEach(() => {
  $toasts.set([]);
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

describe('addToast', () => {
  it('adds a toast to the store', () => {
    addToast('Algo salió mal');
    expect($toasts.get()).toHaveLength(1);
    expect($toasts.get()[0].message).toBe('Algo salió mal');
    expect($toasts.get()[0].type).toBe('error');
  });

  it('adds a success toast with correct type', () => {
    addToast('Guardado correctamente', 'success');
    expect($toasts.get()[0].type).toBe('success');
  });

  it('dismissToast removes the correct toast', () => {
    addToast('Toast 1');
    addToast('Toast 2');
    const id = $toasts.get()[0].id;
    dismissToast(id);
    expect($toasts.get()).toHaveLength(1);
    expect($toasts.get()[0].message).toBe('Toast 2');
  });

  it('caps at 3 toasts — 4th call is ignored', () => {
    addToast('A');
    addToast('B');
    addToast('C');
    addToast('D');
    expect($toasts.get()).toHaveLength(3);
  });

  it('auto-dismisses after 5000ms', () => {
    addToast('Auto-dismiss me');
    expect($toasts.get()).toHaveLength(1);
    vi.advanceTimersByTime(5_000);
    expect($toasts.get()).toHaveLength(0);
  });
});

// Feature: profile-frontend, Property 11: Toast Maximum Simultaneous Count
describe('Property 11: Toast Maximum Simultaneous Count', () => {
  it('never shows more than 3 toasts simultaneously for any sequence of calls', () => {
    fc.assert(
      fc.property(
        fc.array(fc.string({ minLength: 1 }), { minLength: 4, maxLength: 20 }),
        (messages) => {
          $toasts.set([]);
          messages.forEach((m) => addToast(m));
          expect($toasts.get().length).toBeLessThanOrEqual(3);
        }
      ),
      { numRuns: 100 }
    );
  });
});

// Feature: profile-frontend, Property 12: Toast Auto-Dismiss
describe('Property 12: Toast Auto-Dismiss', () => {
  it('removes any toast after 5000ms', () => {
    fc.assert(
      fc.property(fc.string({ minLength: 1 }), (message) => {
        $toasts.set([]);
        addToast(message);
        expect($toasts.get().length).toBe(1);
        vi.advanceTimersByTime(5_000);
        expect($toasts.get().length).toBe(0);
      }),
      { numRuns: 100 }
    );
  });
});
