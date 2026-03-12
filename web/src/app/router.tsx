import { createBrowserRouter } from 'react-router-dom';
import Layout from '@/components/layout/Layout';
import ProfilePage from '@/pages/ProfilePage';

export const router = createBrowserRouter([
  {
    element: <Layout />,
    children: [{ path: '/', element: <ProfilePage /> }],
  },
]);
