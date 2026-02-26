"""Application DTOs for profile endpoints."""

from __future__ import annotations

from pydantic import BaseModel

from src.domain.entities.profile import UserProfile


class UpdateContactRequest(BaseModel):
    phone: str | None = None
    street: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str | None = None


class UpdatePersonalRequest(BaseModel):
    full_name: str | None = None
    date_of_birth: str | None = None


class UpdatePreferencesRequest(BaseModel):
    notification_preferences_email: bool | None = None
    notification_preferences_sms: bool | None = None
    notification_preferences_whatsapp: bool | None = None
    language: str | None = None
    timezone: str | None = None


class UpdateDisplayRequest(BaseModel):
    bio: str | None = None
    display_name: str | None = None


class AddressResponse(BaseModel):
    street: str
    city: str
    state: str
    postal_code: str
    country: str


class NotificationPreferencesResponse(BaseModel):
    email: bool
    sms: bool
    whatsapp: bool


class ProfileResponse(BaseModel):
    user_id: str
    email: str
    full_name: str
    phone: str
    date_of_birth: str
    address: AddressResponse
    email_verified: bool
    avatar_url: str | None
    bio: str | None
    display_name: str | None
    language: str
    timezone: str
    notification_preferences: NotificationPreferencesResponse
    deleted_at: str | None

    @classmethod
    def from_domain(cls, profile: UserProfile) -> ProfileResponse:
        return cls(
            user_id=str(profile.user_id),
            email=profile.email,
            full_name=profile.full_name,
            phone=profile.phone,
            date_of_birth=profile.date_of_birth,
            address=AddressResponse(
                street=profile.address.street,
                city=profile.address.city,
                state=profile.address.state,
                postal_code=profile.address.postal_code,
                country=profile.address.country,
            ),
            email_verified=profile.email_verified,
            avatar_url=profile.avatar_url,
            bio=profile.bio,
            display_name=profile.display_name,
            language=profile.language,
            timezone=profile.timezone,
            notification_preferences=NotificationPreferencesResponse(
                email=profile.notification_preferences.email,
                sms=profile.notification_preferences.sms,
                whatsapp=profile.notification_preferences.whatsapp,
            ),
            deleted_at=profile.deleted_at.isoformat() if profile.deleted_at is not None else None,
        )
