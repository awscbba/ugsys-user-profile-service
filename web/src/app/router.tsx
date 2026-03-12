import { createBrowserRouter } from 'react-router-dom';
import Layout from '@/components/layout/Layout';
import ProfilePage from '@/pages/ProfilePage';
import LoginPage from '@/pages/LoginPage';

export const router = createBrowserRouter([
  // Public routes — no AuthGate
  { path: '/login', element: <LoginPage /> },

  // Protected routes — wrapped in Layout → AuthGate
  {
    element: <Layout />,
    children: [{ path: '/', element: <ProfilePage /> }],
  },
]);
