"""Unit tests for ProfileService application service."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.application.commands.profile_commands import (
    CreateProfileCommand,
    DeleteProfileCommand,
    UpdateContactCommand,
    UpdatePersonalCommand,
)
from src.application.queries.profile_queries import GetProfileQuery
from src.application.services.profile_service import ProfileService
from src.domain.entities.profile import UserProfile


def make_profile(user_id=None, **kwargs) -> UserProfile:
    uid = user_id or uuid4()
    return UserProfile(
        user_id=uid,
        email="[email]",
        full_name="Test User",
        **kwargs,
    )


def make_service(profile=None):
    repo = AsyncMock()
    publisher = MagicMock()
    if profile:
        repo.find_by_user_id.return_value = profile
        repo.save.return_value = profile
        repo.update.return_value = profile
    else:
        repo.find_by_user_id.return_value = None
    return ProfileService(profile_repo=repo, event_publisher=publisher), repo, publisher


# ── get_profile ───────────────────────────────────────────────────────────────


async def test_get_profile_own():
    uid = uuid4()
    profile = make_profile(user_id=uid)
    svc, _repo, _ = make_service(profile)
    result = await svc.get_profile(GetProfileQuery(user_id=uid, requester_id=str(uid)))
    assert result.user_id == uid


async def test_get_profile_admin_can_access_any():
    uid = uuid4()
    admin_id = str(uuid4())
    profile = make_profile(user_id=uid)
    svc, _, _ = make_service(profile)
    result = await svc.get_profile(
        GetProfileQuery(user_id=uid, requester_id=admin_id, is_admin=True)
    )
    assert result.user_id == uid


async def test_get_profile_idor_blocked():
    uid = uuid4()
    other_id = str(uuid4())
    profile = make_profile(user_id=uid)
    svc, _, _ = make_service(profile)
    with pytest.raises(PermissionError):
        await svc.get_profile(GetProfileQuery(user_id=uid, requester_id=other_id, is_admin=False))


async def test_get_profile_not_found():
    svc, _, _ = make_service()
    with pytest.raises(ValueError, match="not found"):
        await svc.get_profile(GetProfileQuery(user_id=uuid4(), requester_id="x"))


# ── create_profile ────────────────────────────────────────────────────────────


async def test_create_profile_success():
    uid = uuid4()
    repo = AsyncMock()
    repo.find_by_user_id.return_value = None
    publisher = MagicMock()
    svc = ProfileService(profile_repo=repo, event_publisher=publisher)
    repo.save.side_effect = lambda p: p

    result = await svc.create_profile(
        CreateProfileCommand(
            user_id=uid,
            email="[email]",
            full_name="Test User",
            phone="+591 70000000",
        )
    )
    assert result.user_id == uid
    assert result.phone == "+591 70000000"
    publisher.publish.assert_called_once()


async def test_create_profile_duplicate_raises():
    uid = uuid4()
    profile = make_profile(user_id=uid)
    svc, _, _ = make_service(profile)
    with pytest.raises(ValueError, match="already exists"):
        await svc.create_profile(CreateProfileCommand(user_id=uid, email="[email]", full_name="X"))


# ── update_contact ────────────────────────────────────────────────────────────


async def test_update_contact_success():
    uid = uuid4()
    profile = make_profile(user_id=uid)
    svc, repo, publisher = make_service(profile)
    repo.update.return_value = profile

    await svc.update_contact(
        UpdateContactCommand(
            user_id=uid,
            requester_id=str(uid),
            phone="+591 70000001",
        )
    )
    publisher.publish.assert_called_once()


async def test_update_contact_idor_blocked():
    uid = uuid4()
    profile = make_profile(user_id=uid)
    svc, _, _ = make_service(profile)
    with pytest.raises(PermissionError):
        await svc.update_contact(
            UpdateContactCommand(
                user_id=uid,
                requester_id=str(uuid4()),
                phone="+591 70000001",
            )
        )


# ── update_personal ───────────────────────────────────────────────────────────


async def test_update_personal_success():
    uid = uuid4()
    profile = make_profile(user_id=uid)
    svc, repo, publisher = make_service(profile)
    repo.update.return_value = profile

    await svc.update_personal(
        UpdatePersonalCommand(
            user_id=uid,
            requester_id=str(uid),
            full_name="New Name",
        )
    )
    publisher.publish.assert_called_once()


# ── delete_profile ────────────────────────────────────────────────────────────


async def test_delete_profile_publishes_event():
    uid = uuid4()
    repo = AsyncMock()
    publisher = MagicMock()
    svc = ProfileService(profile_repo=repo, event_publisher=publisher)

    await svc.delete_profile(DeleteProfileCommand(user_id=uid))
    repo.delete.assert_called_once_with(uid)
    publisher.publish.assert_called_once()
