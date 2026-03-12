import { Navigate, useLocation } from 'react-router-dom';
import { useStore } from '@nanostores/react';
import { $isInitializing, $isAuthenticated } from '../../stores/authStore';

interface AuthGateProps {
  children: React.ReactNode;
}

export default function AuthGate({ children }: AuthGateProps) {
  const isInitializing = useStore($isInitializing);
  const isAuthenticated = useStore($isAuthenticated);
  const location = useLocation();

  if (isInitializing) {
    return (
      <div
        className="flex items-center justify-center min-h-screen"
        role="status"
        aria-label="Cargando"
      >
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#FF9900]" />
      </div>
    );
  }

  if (!isAuthenticated) {
    const redirect = encodeURIComponent(location.pathname + location.search);
    return <Navigate to={`/login?redirect=${redirect}`} replace />;
  }

  return <>{children}</>;
}
