"""Integration tests for DynamoDBProfileRepository using moto."""

from datetime import UTC, datetime
from uuid import uuid4

from src.domain.entities.profile import Address, UserProfile
from src.domain.value_objects.notification_preferences import NotificationPreferences


def make_profile(**kwargs) -> UserProfile:  # type: ignore[no-untyped-def]
    return UserProfile(
        user_id=kwargs.get("user_id", uuid4()),
        email=kwargs.get("email", "[email]"),
        full_name=kwargs.get("full_name", "Test User"),
        phone=kwargs.get("phone", "+591 70000000"),
        date_of_birth=kwargs.get("date_of_birth", "1990-01-01"),
        address=Address(
            street="Calle Falsa 123",
            city="Cochabamba",
            state="Cochabamba",
            postal_code="0000",
            country="Bolivia",
        ),
        email_verified=kwargs.get("email_verified", True),
        notification_preferences=NotificationPreferences(email=True, sms=True, whatsapp=False),
        language="es",
        timezone="America/La_Paz",
        avatar_url=kwargs.get("avatar_url"),
        bio=kwargs.get("bio"),
        display_name=kwargs.get("display_name"),
    )


# ── Round-trip ────────────────────────────────────────────────────────────────


async def test_save_and_find_round_trip(profile_repo) -> None:  # type: ignore[no-untyped-def]
    """Saving a profile and finding it by user_id returns an identical profile."""
    profile = make_profile(
        avatar_url="https://cdn.example.com/avatar.jpg",
        bio="Hello world",
        display_name="tester",
    )
    await profile_repo.save(profile)

    found = await profile_repo.find_by_user_id(profile.user_id)

    assert found is not None
    assert found.user_id == profile.user_id
    assert found.email == profile.email
    assert found.full_name == profile.full_name
    assert found.phone == profile.phone
    assert found.avatar_url == "https://cdn.example.com/avatar.jpg"
    assert found.bio == "Hello world"
    assert found.display_name == "tester"
    assert found.language == "es"
    assert found.timezone == "America/La_Paz"
    assert found.notification_preferences.email is True
    assert found.notification_preferences.sms is True
    assert found.notification_preferences.whatsapp is False


async def test_find_returns_none_for_missing(profile_repo) -> None:  # type: ignore[no-untyped-def]
    found = await profile_repo.find_by_user_id(uuid4())
    assert found is None


async def test_update_persists_changes(profile_repo) -> None:  # type: ignore[no-untyped-def]
    profile = make_profile()
    await profile_repo.save(profile)

    profile.full_name = "Updated Name"
    profile.bio = "Updated bio"
    await profile_repo.update(profile)

    found = await profile_repo.find_by_user_id(profile.user_id)
    assert found is not None
    assert found.full_name == "Updated Name"
    assert found.bio == "Updated bio"


# ── Backward compatibility ────────────────────────────────────────────────────


async def test_legacy_item_missing_new_fields_uses_defaults(profile_repo, dynamodb_table) -> None:  # type: ignore[no-untyped-def]
    """Items written before new fields existed should deserialize with safe defaults."""
    uid = uuid4()
    # Write a minimal legacy item directly — no notification_preferences, language, timezone, etc.
    dynamodb_table.put_item(
        Item={
            "pk": f"PROFILE#{uid}",
            "sk": "PROFILE",
            "user_id": str(uid),
            "email": "[email]",
            "full_name": "Legacy User",
            "phone": "",
            "date_of_birth": "",
            "address": {"street": "", "city": "", "state": "", "postal_code": "", "country": ""},
            "email_verified": False,
            "require_password_change": False,
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
        }
    )

    found = await profile_repo.find_by_user_id(uid)

    assert found is not None
    assert found.language == "es"
    assert found.timezone == "America/La_Paz"
    assert found.notification_preferences.email is True
    assert found.notification_preferences.sms is False
    assert found.notification_preferences.whatsapp is False
    assert found.avatar_url is None
    assert found.bio is None
    assert found.display_name is None
    assert found.deleted_at is None


# ── list_profiles ─────────────────────────────────────────────────────────────


async def test_list_profiles_returns_correct_page(profile_repo) -> None:  # type: ignore[no-untyped-def]
    """list_profiles returns the correct page slice and total count."""
    profiles = [make_profile() for _ in range(5)]
    for p in profiles:
        await profile_repo.save(p)

    page1, total = await profile_repo.list_profiles(page=1, page_size=3)
    assert total == 5
    assert len(page1) == 3

    page2, total2 = await profile_repo.list_profiles(page=2, page_size=3)
    assert total2 == 5
    assert len(page2) == 2


async def test_list_profiles_excludes_soft_deleted(profile_repo) -> None:  # type: ignore[no-untyped-def]
    """Soft-deleted profiles must not appear in list_profiles results."""
    active = make_profile()
    deleted = make_profile()
    await profile_repo.save(active)
    await profile_repo.save(deleted)

    # Soft-delete one
    deleted.soft_delete()
    await profile_repo.update(deleted)

    results, total = await profile_repo.list_profiles(page=1, page_size=10)

    assert total == 1
    assert all(p.user_id != deleted.user_id for p in results)


async def test_list_profiles_empty_table(profile_repo) -> None:  # type: ignore[no-untyped-def]
    results, total = await profile_repo.list_profiles(page=1, page_size=10)
    assert results == []
    assert total == 0


# ── delete ────────────────────────────────────────────────────────────────────


async def test_delete_removes_item(profile_repo) -> None:  # type: ignore[no-untyped-def]
    profile = make_profile()
    await profile_repo.save(profile)
    await profile_repo.delete(profile.user_id)
    found = await profile_repo.find_by_user_id(profile.user_id)
    assert found is None
