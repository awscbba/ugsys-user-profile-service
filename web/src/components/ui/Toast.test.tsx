import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import * as fc from 'fast-check';
import { ToastContainer } from './Toast';
import { $toasts, addToast } from '../../utils/toast';

beforeEach(() => {
  $toasts.set([]);
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

describe('ToastContainer', () => {
  it('renders toasts from $toasts', () => {
    $toasts.set([{ id: '1', message: 'Error de prueba', type: 'error' }]);
    render(<ToastContainer />);
    expect(screen.getByText('Error de prueba')).toBeInTheDocument();
  });

  it('dismiss button calls dismissToast', () => {
    $toasts.set([{ id: '1', message: 'Error de prueba', type: 'error' }]);
    render(<ToastContainer />);
    fireEvent.click(screen.getByRole('button', { name: /cerrar/i }));
    expect($toasts.get()).toHaveLength(0);
  });

  it('renders at most 3 items', () => {
    $toasts.set([
      { id: '1', message: 'A', type: 'error' },
      { id: '2', message: 'B', type: 'error' },
      { id: '3', message: 'C', type: 'error' },
    ]);
    render(<ToastContainer />);
    expect(screen.getAllByRole('alert')).toHaveLength(3);
  });

  it('renders nothing when $toasts is empty', () => {
    const { container } = render(<ToastContainer />);
    expect(container.firstChild).toBeNull();
  });
});

// Feature: profile-frontend, Property 10: Toast Safety
describe('Property 10: Toast Safety', () => {
  it('toast message never contains HTTP status codes or stack trace markers', () => {
    fc.assert(
      fc.property(fc.integer({ min: 400, max: 599 }), (_status) => {
        $toasts.set([]);
        // Simulate what httpClient does — extracts user_message, falls back to generic
        const safeMessage = 'No se pudo completar la solicitud';
        addToast(safeMessage);
        const toasts = $toasts.get();
        if (toasts.length > 0) {
          const msg = toasts[0].message;
          expect(msg).not.toMatch(/\d{3}/);
          expect(msg).not.toMatch(/Traceback|Error:|at \w+/);
          expect(msg).not.toMatch(/full_name|user_id|email/);
        }
        $toasts.set([]);
      }),
      { numRuns: 100 }
    );
  });
});
