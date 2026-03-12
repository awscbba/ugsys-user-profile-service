/// <reference types="vitest" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import path from 'path';

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8002',
        changeOrigin: true,
      },
      '/auth-api': {
        target: 'http://localhost:8001',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/auth-api/, ''),
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
    coverage: {
      provider: 'v8',
      include: [
        'src/stores/authStore.ts',
        'src/stores/profileStore.ts',
        'src/utils/toast.ts',
        'src/hooks/useEditSection.ts',
        'src/services/httpClient.ts',
        'src/services/authService.ts',
        'src/services/profileService.ts',
        'src/components/layout/AuthGate.tsx',
        'src/components/profile/PersonalSection.tsx',
        'src/components/profile/ContactSection.tsx',
        'src/components/profile/DisplaySection.tsx',
        'src/components/profile/PreferencesSection.tsx',
        'src/components/profile/AvatarUploader.tsx',
        'src/components/ui/Toast.tsx',
        'src/pages/ProfilePage.tsx',
      ],
      thresholds: {
        lines: 80,
        functions: 80,
        branches: 80,
        statements: 80,
      },
    },
  },
});
