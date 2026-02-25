"""Unit tests for new ProfileService methods added in phase 1."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.application.commands.profile_commands import (
    DeleteAvatarCommand,
    SoftDeleteProfileCommand,
    UpdateDisplayCommand,
    UpdatePreferencesCommand,
    UploadAvatarCommand,
)
from src.application.queries.profile_queries import ListProfilesQuery
from src.application.services.profile_service import ProfileService
from src.domain.entities.profile import UserProfile
from src.domain.exceptions import (
    AuthorizationError,
    ExternalServiceError,
    NotFoundError,
    ValidationError,
)


def make_profile(user_id=None, **kwargs) -> UserProfile:
    uid = user_id or uuid4()
    return UserProfile(user_id=uid, email="[email]", full_name="Test User", **kwargs)


def make_service(profile=None, avatar_storage=None):
    repo = AsyncMock()
    publisher = AsyncMock()
    if profile:
        repo.find_by_user_id.return_value = profile
        repo.update.return_value = profile
    else:
        repo.find_by_user_id.return_value = None
    svc = ProfileService(
        profile_repo=repo,
        event_publisher=publisher,
        avatar_storage=avatar_storage,
    )
    return svc, repo, publisher


# ── upload_avatar ─────────────────────────────────────────────────────────────


async def test_upload_avatar_success():
    uid = uuid4()
    profile = make_profile(user_id=uid)
    storage = AsyncMock()
    storage.upload.return_value = "https://bucket.s3.amazonaws.com/avatars/x.jpg"
    svc, repo, publisher = make_service(profile, avatar_storage=storage)

    result = await svc.upload_avatar(
        UploadAvatarCommand(
            user_id=uid,
            requester_id=str(uid),
            is_admin=False,
            file_bytes=b"fake-jpeg-data",
            content_type="image/jpeg",
        )
    )
    storage.upload.assert_called_once()
    repo.update.assert_called_once()
    publisher.publish.assert_called_once()
    assert result.avatar_url == "https://bucket.s3.amazonaws.com/avatars/x.jpg"


async def test_upload_avatar_invalid_content_type():
    uid = uuid4()
    profile = make_profile(user_id=uid)
    svc, _, _ = make_service(profile)

    with pytest.raises(ValidationError) as exc_info:
        await svc.upload_avatar(
            UploadAvatarCommand(
                user_id=uid,
                requester_id=str(uid),
                is_admin=False,
                file_bytes=b"data",
                content_type="image/gif",
            )
        )
    assert "JPEG, PNG, or WebP" in exc_info.value.user_message


async def test_upload_avatar_too_large():
    uid = uuid4()
    profile = make_profile(user_id=uid)
    svc, _, _ = make_service(profile)

    with pytest.raises(ValidationError) as exc_info:
        await svc.upload_avatar(
            UploadAvatarCommand(
                user_id=uid,
                requester_id=str(uid),
                is_admin=False,
                file_bytes=b"x" * (5 * 1024 * 1024 + 1),
                content_type="image/png",
            )
        )
    assert "5 MB" in exc_info.value.user_message


async def test_upload_avatar_idor_blocked():
    uid = uuid4()
    profile = make_profile(user_id=uid)
    svc, _, _ = make_service(profile)

    with pytest.raises(AuthorizationError):
        await svc.upload_avatar(
            UploadAvatarCommand(
                user_id=uid,
                requester_id=str(uuid4()),
                is_admin=False,
                file_bytes=b"data",
                content_type="image/jpeg",
            )
        )


async def test_upload_avatar_no_storage_raises():
    uid = uuid4()
    profile = make_profile(user_id=uid)
    svc, _, _ = make_service(profile, avatar_storage=None)

    with pytest.raises(ExternalServiceError):
        await svc.upload_avatar(
            UploadAvatarCommand(
                user_id=uid,
                requester_id=str(uid),
                is_admin=False,
                file_bytes=b"data",
                content_type="image/jpeg",
            )
        )


async def test_upload_avatar_profile_not_found():
    svc, _, _ = make_service(profile=None)
    with pytest.raises(NotFoundError):
        await svc.upload_avatar(
            UploadAvatarCommand(
                user_id=uuid4(),
                requester_id="x",
                is_admin=False,
                file_bytes=b"data",
                content_type="image/jpeg",
            )
        )


# ── delete_avatar ─────────────────────────────────────────────────────────────


async def test_delete_avatar_clears_url():
    uid = uuid4()
    profile = make_profile(user_id=uid, avatar_url="https://bucket/avatars/x.jpg")
    storage = AsyncMock()
    svc, _repo, _ = make_service(profile, avatar_storage=storage)

    result = await svc.delete_avatar(
        DeleteAvatarCommand(user_id=uid, requester_id=str(uid), is_admin=False)
    )
    storage.delete.assert_called_once()
    assert result.avatar_url is None


async def test_delete_avatar_no_avatar_succeeds():
    uid = uuid4()
    profile = make_profile(user_id=uid, avatar_url=None)
    storage = AsyncMock()
    svc, _, _ = make_service(profile, avatar_storage=storage)

    result = await svc.delete_avatar(
        DeleteAvatarCommand(user_id=uid, requester_id=str(uid), is_admin=False)
    )
    storage.delete.assert_not_called()
    assert result.avatar_url is None


async def test_delete_avatar_idor_blocked():
    uid = uuid4()
    profile = make_profile(user_id=uid)
    svc, _, _ = make_service(profile)

    with pytest.raises(AuthorizationError):
        await svc.delete_avatar(
            DeleteAvatarCommand(user_id=uid, requester_id=str(uuid4()), is_admin=False)
        )


async def test_delete_avatar_not_found():
    svc, _, _ = make_service(profile=None)
    with pytest.raises(NotFoundError):
        await svc.delete_avatar(
            DeleteAvatarCommand(user_id=uuid4(), requester_id="x", is_admin=False)
        )


# ── update_preferences ────────────────────────────────────────────────────────


async def test_update_preferences_success():
    uid = uuid4()
    profile = make_profile(user_id=uid)
    svc, repo, publisher = make_service(profile)

    result = await svc.update_preferences(
        UpdatePreferencesCommand(
            user_id=uid,
            requester_id=str(uid),
            is_admin=False,
            language="en",
            timezone="UTC",
        )
    )
    repo.update.assert_called_once()
    publisher.publish.assert_called_once()
    assert result.language == "en"


async def test_update_preferences_idor_blocked():
    uid = uuid4()
    profile = make_profile(user_id=uid)
    svc, _, _ = make_service(profile)

    with pytest.raises(AuthorizationError):
        await svc.update_preferences(
            UpdatePreferencesCommand(
                user_id=uid,
                requester_id=str(uuid4()),
                is_admin=False,
                language="en",
            )
        )


async def test_update_preferences_not_found():
    svc, _, _ = make_service(profile=None)
    with pytest.raises(NotFoundError):
        await svc.update_preferences(
            UpdatePreferencesCommand(
                user_id=uuid4(), requester_id="x", is_admin=False, language="en"
            )
        )


async def test_update_preferences_notification_fields():
    uid = uuid4()
    profile = make_profile(user_id=uid)
    svc, _repo, publisher = make_service(profile)

    await svc.update_preferences(
        UpdatePreferencesCommand(
            user_id=uid,
            requester_id=str(uid),
            is_admin=False,
            notification_preferences_sms=True,
        )
    )
    publisher.publish.assert_called_once()


# ── update_display ────────────────────────────────────────────────────────────


async def test_update_display_success():
    uid = uuid4()
    profile = make_profile(user_id=uid)
    svc, repo, publisher = make_service(profile)

    await svc.update_display(
        UpdateDisplayCommand(
            user_id=uid,
            requester_id=str(uid),
            is_admin=False,
            bio="Hello",
            display_name="Dev",
        )
    )
    repo.update.assert_called_once()
    publisher.publish.assert_called_once()


async def test_update_display_bio_too_long():
    uid = uuid4()
    profile = make_profile(user_id=uid)
    svc, _, _ = make_service(profile)

    with pytest.raises(ValidationError) as exc_info:
        await svc.update_display(
            UpdateDisplayCommand(
                user_id=uid,
                requester_id=str(uid),
                is_admin=False,
                bio="x" * 501,
            )
        )
    assert "500" in exc_info.value.user_message


async def test_update_display_idor_blocked():
    uid = uuid4()
    profile = make_profile(user_id=uid)
    svc, _, _ = make_service(profile)

    with pytest.raises(AuthorizationError):
        await svc.update_display(
            UpdateDisplayCommand(
                user_id=uid,
                requester_id=str(uuid4()),
                is_admin=False,
                bio="Hello",
            )
        )


async def test_update_display_not_found():
    svc, _, _ = make_service(profile=None)
    with pytest.raises(NotFoundError):
        await svc.update_display(
            UpdateDisplayCommand(
                user_id=uuid4(), requester_id="x", is_admin=False, bio="Hello"
            )
        )


# ── list_profiles ─────────────────────────────────────────────────────────────


async def test_list_profiles_admin_success():
    uid = uuid4()
    profile = make_profile(user_id=uid)
    repo = AsyncMock()
    repo.list_profiles.return_value = ([profile], 1)
    publisher = AsyncMock()
    svc = ProfileService(profile_repo=repo, event_publisher=publisher)

    profiles, total = await svc.list_profiles(
        ListProfilesQuery(requester_id="admin", is_admin=True, page=1, page_size=20)
    )
    assert total == 1
    assert len(profiles) == 1


async def test_list_profiles_caps_page_size():
    repo = AsyncMock()
    repo.list_profiles.return_value = ([], 0)
    svc = ProfileService(profile_repo=repo)

    await svc.list_profiles(
        ListProfilesQuery(requester_id="admin", is_admin=True, page=1, page_size=200)
    )
    repo.list_profiles.assert_called_once_with(page=1, page_size=100)


async def test_list_profiles_non_admin_blocked():
    repo = AsyncMock()
    svc = ProfileService(profile_repo=repo)

    with pytest.raises(AuthorizationError):
        await svc.list_profiles(
            ListProfilesQuery(requester_id="user", is_admin=False, page=1, page_size=20)
        )


# ── soft_delete_profile ───────────────────────────────────────────────────────


async def test_soft_delete_success():
    uid = uuid4()
    profile = make_profile(user_id=uid)
    svc, repo, publisher = make_service(profile)

    await svc.soft_delete_profile(
        SoftDeleteProfileCommand(user_id=uid, requester_id="admin")
    )
    repo.update.assert_called_once()
    publisher.publish.assert_called_once()
    assert profile.deleted_at is not None


async def test_soft_delete_not_found():
    svc, _, _ = make_service(profile=None)
    with pytest.raises(NotFoundError):
        await svc.soft_delete_profile(
            SoftDeleteProfileCommand(user_id=uuid4(), requester_id="admin")
        )
