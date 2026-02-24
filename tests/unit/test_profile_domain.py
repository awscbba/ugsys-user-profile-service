"""Unit tests for UserProfile domain entity."""

from uuid import uuid4

from src.domain.entities.profile import Address, UserProfile


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
