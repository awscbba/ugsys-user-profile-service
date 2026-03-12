import '@testing-library/jest-dom';
import { afterEach, vi } from 'vitest';

// Restore real timers after each test so fake-timer tests don't bleed into others.
afterEach(() => {
  vi.useRealTimers();
});
