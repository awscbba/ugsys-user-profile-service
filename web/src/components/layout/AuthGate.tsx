import { useStore } from '@nanostores/react';
import { $isInitializing, $isAuthenticated } from '../../stores/authStore';

interface AuthGateProps {
  children: React.ReactNode;
}

export default function AuthGate({ children }: AuthGateProps) {
  const isInitializing = useStore($isInitializing);
  const isAuthenticated = useStore($isAuthenticated);

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

  // Safety net — redirect is already handled inside initializeAuth()
  if (!isAuthenticated) {
    return null;
  }

  return <>{children}</>;
}
