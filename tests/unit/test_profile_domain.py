"""Unit tests for UserProfile domain entity."""

from datetime import UTC, datetime
from uuid import uuid4

from src.domain.entities.profile import Address, UserProfile
from src.domain.value_objects.notification_preferences import NotificationPreferences


def make_profile(**kwargs) -> UserProfile:
    defaults = dict(
        user_id=uuid4(),
        email="[email]",
        full_name="Test User",
    )
    defaults.update(kwargs)
    return UserProfile(**defaults)


def test_profile_defaults():
    p = make_profile()
    assert p.phone == ""
    assert p.date_of_birth == ""
    assert p.email_verified is False
    assert p.require_password_change is False
    assert p.address.city == ""


def test_update_contact_phone():
    p = make_profile()
    before = p.updated_at
    p.update_contact(phone="+591 70000000")
    assert p.phone == "+591 70000000"
    assert p.updated_at >= before


def test_update_contact_address():
    p = make_profile()
    addr = Address(street="Av. Heroinas", city="Cochabamba", country="Bolivia")
    p.update_contact(address=addr)
    assert p.address.city == "Cochabamba"
    assert p.address.country == "Bolivia"


def test_update_personal():
    p = make_profile()
    p.update_personal(full_name="New Name", date_of_birth="1990-01-15")
    assert p.full_name == "New Name"
    assert p.date_of_birth == "1990-01-15"


def test_mark_email_verified():
    p = make_profile(email_verified=False)
    p.mark_email_verified()
    assert p.email_verified is True


def test_clear_password_change_flag():
    p = make_profile(require_password_change=True)
    p.clear_password_change_flag()
    assert p.require_password_change is False


def test_update_contact_partial_does_not_clear_phone():
    p = make_profile(phone="+591 70000000")
    addr = Address(city="La Paz")
    p.update_contact(address=addr)
    # phone unchanged when not passed
    assert p.phone == "+591 70000000"


# ── New field and method tests ────────────────────────────────────────────────


def test_new_field_defaults():
    p = make_profile()
    assert p.language == "es"
    assert p.timezone == "America/La_Paz"
    assert p.avatar_url is None
    assert p.bio is None
    assert p.display_name is None
    assert p.deleted_at is None
    assert p.notification_preferences.email is True
    assert p.notification_preferences.sms is False
    assert p.notification_preferences.whatsapp is False


def test_update_preferences_language_only():
    p = make_profile()
    p.update_preferences(language="en")
    assert p.language == "en"
    assert p.timezone == "America/La_Paz"  # unchanged


def test_update_preferences_timezone_only():
    p = make_profile()
    p.update_preferences(timezone="America/New_York")
    assert p.timezone == "America/New_York"
    assert p.language == "es"  # unchanged


def test_update_preferences_notification():
    p = make_profile()
    prefs = NotificationPreferences(email=False, sms=True, whatsapp=False)
    p.update_preferences(notification_preferences=prefs)
    assert p.notification_preferences.email is False
    assert p.notification_preferences.sms is True


def test_update_display_bio_and_name():
    p = make_profile()
    p.update_display(bio="Hello world", display_name="Dev")
    assert p.bio == "Hello world"
    assert p.display_name == "Dev"


def test_update_display_bio_truncated():
    p = make_profile()
    long_bio = "x" * 600
    p.update_display(bio=long_bio)
    assert len(p.bio) == 500


def test_update_display_partial_does_not_clear():
    p = make_profile()
    p.update_display(bio="Initial bio")
    p.update_display(display_name="Dev")
    assert p.bio == "Initial bio"  # unchanged
    assert p.display_name == "Dev"


def test_soft_delete_sets_deleted_at():
    p = make_profile()
    assert p.deleted_at is None
    before = datetime.now(UTC)
    p.soft_delete()
    assert p.deleted_at is not None
    assert p.deleted_at >= before
    assert p.updated_at >= before
