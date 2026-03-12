import React from 'react';
import ReactDOM from 'react-dom/client';
import { RouterProvider } from 'react-router-dom';
import { router } from './app/router';
import { initializeAuth } from './stores/authStore';
import './index.css';

async function renderApp() {
  await initializeAuth();

  const rootElement = document.getElementById('root');
  if (!rootElement) {
    console.error('[App] #root element not found — cannot mount React app');
    return;
  }

  ReactDOM.createRoot(rootElement).render(
    <React.StrictMode>
      <RouterProvider router={router} />
    </React.StrictMode>
  );
}

renderApp();
