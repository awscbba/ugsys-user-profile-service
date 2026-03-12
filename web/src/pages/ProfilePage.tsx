import { useEffect } from 'react';
import { useStore } from '@nanostores/react';
import { $profile, $profileLoading, loadProfile } from '../stores/profileStore';
import AvatarUploader from '../components/profile/AvatarUploader';
import PersonalSection from '../components/profile/PersonalSection';
import ContactSection from '../components/profile/ContactSection';
import DisplaySection from '../components/profile/DisplaySection';
import PreferencesSection from '../components/profile/PreferencesSection';

function ProfileSkeleton() {
  return (
    <div className="animate-pulse space-y-4" aria-label="Cargando perfil">
      {[1, 2, 3, 4].map((i) => (
        <div key={i} className="bg-gray-200 rounded-lg h-32" />
      ))}
    </div>
  );
}

export default function ProfilePage() {
  const profile = useStore($profile);
  const isLoading = useStore($profileLoading);

  useEffect(() => {
    loadProfile();
  }, []);

  const displayName = profile?.display_name ?? profile?.full_name ?? '';

  return (
    <div className="max-w-2xl mx-auto px-4 py-8 space-y-6">
      {isLoading && !profile ? (
        <ProfileSkeleton />
      ) : profile ? (
        <>
          <div className="text-center">
            <h1 className="text-2xl font-bold text-gray-900">{displayName}</h1>
            <p className="text-sm text-gray-500">{profile.email}</p>
          </div>

          <AvatarUploader avatarUrl={profile.avatar_url} userId={profile.user_id} />
          <PersonalSection />
          <ContactSection />
          <DisplaySection />
          <PreferencesSection />
        </>
      ) : null}
    </div>
  );
}
