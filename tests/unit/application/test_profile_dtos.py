"""Unit tests for application DTOs — profile_dtos.py.

TDD: these tests are written FIRST and will fail (RED) until profile_dtos.py is implemented.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from src.application.dtos.profile_dtos import (
    ProfileResponse,
    UpdateContactRequest,
    UpdateDisplayRequest,
    UpdatePersonalRequest,
    UpdatePreferencesRequest,
)
from src.domain.entities.profile import Address, UserProfile
from src.domain.value_objects.notification_preferences import NotificationPreferences

# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_profile(
    user_id: UUID | None = None,
    deleted_at: datetime | None = None,
) -> UserProfile:
    return UserProfile(
        user_id=user_id or uuid4(),
        email="dev@example.com",
        full_name="Dev User",
        phone="+591 70000000",
        date_of_birth="1990-01-15",
        address=Address(
            street="Calle Sucre 123",
            city="Cochabamba",
            state="Cochabamba",
            postal_code="0000",
            country="Bolivia",
        ),
        email_verified=True,
        require_password_change=False,
        notification_preferences=NotificationPreferences(email=True, sms=False, whatsapp=True),
        language="es",
        timezone="America/La_Paz",
        avatar_url="https://example.com/avatar.jpg",
        bio="Hello world",
        display_name="devuser",
        deleted_at=deleted_at,
    )


# ── Request DTO instantiation ─────────────────────────────────────────────────


def test_update_contact_request_all_none() -> None:
    req = UpdateContactRequest()
    assert req.phone is None
    assert req.street is None
    assert req.city is None
    assert req.state is None
    assert req.postal_code is None
    assert req.country is None


def test_update_personal_request_all_none() -> None:
    req = UpdatePersonalRequest()
    assert req.full_name is None
    assert req.date_of_birth is None


def test_update_preferences_request_all_none() -> None:
    req = UpdatePreferencesRequest()
    assert req.notification_preferences_email is None
    assert req.notification_preferences_sms is None
    assert req.notification_preferences_whatsapp is None
    assert req.language is None
    assert req.timezone is None


def test_update_display_request_all_none() -> None:
    req = UpdateDisplayRequest()
    assert req.bio is None
    assert req.display_name is None


# ── ProfileResponse.from_domain() ─────────────────────────────────────────────


def test_profile_response_from_domain_maps_all_fields() -> None:
    uid = uuid4()
    profile = _make_profile(user_id=uid)

    resp = ProfileResponse.from_domain(profile)

    assert resp.user_id == str(uid)
    assert resp.email == "dev@example.com"
    assert resp.full_name == "Dev User"
    assert resp.phone == "+591 70000000"
    assert resp.date_of_birth == "1990-01-15"
    assert resp.address.street == "Calle Sucre 123"
    assert resp.address.city == "Cochabamba"
    assert resp.address.state == "Cochabamba"
    assert resp.address.postal_code == "0000"
    assert resp.address.country == "Bolivia"
    assert resp.email_verified is True
    assert resp.avatar_url == "https://example.com/avatar.jpg"
    assert resp.bio == "Hello world"
    assert resp.display_name == "devuser"
    assert resp.language == "es"
    assert resp.timezone == "America/La_Paz"
    assert resp.notification_preferences.email is True
    assert resp.notification_preferences.sms is False
    assert resp.notification_preferences.whatsapp is True


def test_profile_response_deleted_at_none_when_not_deleted() -> None:
    profile = _make_profile(deleted_at=None)
    resp = ProfileResponse.from_domain(profile)
    assert resp.deleted_at is None


def test_profile_response_deleted_at_isoformat_when_deleted() -> None:
    ts = datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC)
    profile = _make_profile(deleted_at=ts)
    resp = ProfileResponse.from_domain(profile)
    assert resp.deleted_at == ts.isoformat()


def test_profile_response_user_id_is_string() -> None:
    uid = uuid4()
    profile = _make_profile(user_id=uid)
    resp = ProfileResponse.from_domain(profile)
    assert isinstance(resp.user_id, str)
    assert resp.user_id == str(uid)
