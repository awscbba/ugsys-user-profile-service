import { Outlet, NavLink } from 'react-router-dom';
import { useStore } from '@nanostores/react';
import { Footer, UserMenu } from '@ugsys/ui-lib';
import type { LinkItem } from '@ugsys/ui-lib';
import { $user, logout } from '../../stores/authStore';
import AuthGate from './AuthGate';
import { ToastContainer } from '../ui/Toast';

const renderLink = ({
  href,
  children,
  className,
  onClick,
  role,
  tabIndex,
  'aria-current': ariaCurrent,
}: {
  href: string;
  children: React.ReactNode;
  className?: string;
  onClick?: React.MouseEventHandler;
  role?: string;
  tabIndex?: number;
  'aria-current'?: React.AriaAttributes['aria-current'];
}) => (
  <NavLink
    to={href}
    className={className}
    onClick={onClick}
    role={role}
    tabIndex={tabIndex}
    aria-current={ariaCurrent}
  >
    {children}
  </NavLink>
);

const footerLinks: LinkItem[] = [
  { label: 'Sitio Principal', href: 'https://cbba.apps.cloud.org.bo/aws', external: true },
  { label: 'Eventos', href: 'https://cbba.apps.cloud.org.bo/aws/events', external: true },
  { label: 'Contacto', href: 'https://cbba.apps.cloud.org.bo/aws/contact', external: true },
];

export default function Layout() {
  const user = useStore($user);

  return (
    <div className="flex flex-col min-h-screen">
      <header
        className="sticky top-0 z-50"
        style={{
          backgroundColor: '#1e2738',
          borderBottom: '1px solid rgba(255,255,255,0.07)',
        }}
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex-shrink-0">
              <span className="text-white font-bold text-base leading-tight">
                AWS User Group Cochabamba
              </span>
              <span className="block text-[#FF9900] text-xs font-medium">Mi Perfil</span>
            </div>
            {user && (
              <UserMenu
                user={{
                  name: user.email,
                  email: user.email,
                  roles: user.roles,
                  avatarUrl: undefined,
                }}
                onLogout={logout}
                adminPanelUrl="https://admin.apps.cloud.org.bo"
                profileHref="https://profile.apps.cloud.org.bo"
                renderLink={renderLink}
              />
            )}
          </div>
        </div>
      </header>

      <main className="flex-1">
        <AuthGate>
          <Outlet />
        </AuthGate>
      </main>

      <Footer year={new Date().getFullYear()} links={footerLinks} renderLink={renderLink} />
      <ToastContainer />
    </div>
  );
}
