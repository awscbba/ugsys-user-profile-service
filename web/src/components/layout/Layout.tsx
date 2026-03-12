import { Outlet, NavLink } from 'react-router-dom';
import { useStore } from '@nanostores/react';
import { Navbar, Footer, UserMenu } from '@ugsys/ui-lib';
import type { LinkItem, RenderLink } from '@ugsys/ui-lib';
import { $user, logout } from '../../stores/authStore';
import AuthGate from './AuthGate';
import { ToastContainer } from '../ui/Toast';

const renderLink: RenderLink = ({
  href,
  children,
  className,
  onClick,
  role,
  tabIndex,
  'aria-current': ariaCurrent,
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
      <Navbar
        links={[]}
        brandSubtitle="Mi Perfil"
        renderLink={renderLink}
        userMenuSlot={
          user ? (
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
          ) : undefined
        }
      />

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
