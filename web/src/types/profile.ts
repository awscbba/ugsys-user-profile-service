export interface AddressResponse {
  street: string;
  city: string;
  state: string;
  postal_code: string;
  country: string;
}

export interface NotificationPreferencesResponse {
  email: boolean;
  sms: boolean;
  whatsapp: boolean;
}

export interface ProfileResponse {
  user_id: string;
  email: string;
  full_name: string;
  phone: string;
  date_of_birth: string;
  address: AddressResponse;
  email_verified: boolean;
  avatar_url: string | null;
  bio: string | null;
  display_name: string | null;
  language: string;
  timezone: string;
  notification_preferences: NotificationPreferencesResponse;
  deleted_at: string | null;
}

export interface UpdatePersonalRequest {
  full_name: string;
  date_of_birth: string;
}

export interface UpdateContactRequest {
  phone: string;
  address: AddressResponse;
}

export interface UpdateDisplayRequest {
  bio: string | null;
  display_name: string | null;
}

export interface UpdatePreferencesRequest {
  notification_preferences: NotificationPreferencesResponse;
  language: string;
  timezone: string;
}
