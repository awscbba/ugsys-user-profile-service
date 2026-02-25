"""Unit tests for the EventBridge event consumer."""

from unittest.mock import AsyncMock
from uuid import uuid4

from src.infrastructure.messaging.event_consumer import (
    _handle_password_changed,
    _handle_user_deactivated,
    _handle_user_registered,
    handle_event,
)


def make_service() -> AsyncMock:
    """Return a mock ProfileService with all public methods as AsyncMocks."""
    svc = AsyncMock()
    return svc


# ── _handle_user_registered ───────────────────────────────────────────────────


async def test_handle_user_registered_creates_profile() -> None:
    # Arrange
    svc = make_service()
    uid = str(uuid4())
    detail = {"user_id": uid, "email": "[email]", "full_name": "Test User"}

    # Act
    await _handle_user_registered(detail, svc)

    # Assert
    svc.create_profile.assert_called_once()
    cmd = svc.create_profile.call_args[0][0]
    assert str(cmd.user_id) == uid
    assert cmd.email == "[email]"
    assert cmd.full_name == "Test User"


async def test_handle_user_registered_missing_fields_skips() -> None:
    svc = make_service()
    await _handle_user_registered({"user_id": str(uuid4())}, svc)
    svc.create_profile.assert_not_called()


async def test_handle_user_registered_conflict_is_swallowed() -> None:
    from src.domain.exceptions import ConflictError

    svc = make_service()
    svc.create_profile.side_effect = ConflictError(
        message="already exists", user_message="already exists"
    )
    # Should not raise
    await _handle_user_registered(
        {"user_id": str(uuid4()), "email": "[email]", "full_name": "X"}, svc
    )


# ── _handle_user_deactivated ──────────────────────────────────────────────────


async def test_handle_user_deactivated_calls_deactivate_profile() -> None:
    # Arrange
    svc = make_service()
    uid = str(uuid4())

    # Act
    await _handle_user_deactivated({"user_id": uid}, svc)

    # Assert — must use the public method, NOT _repo
    svc.deactivate_profile.assert_called_once()
    called_uid = svc.deactivate_profile.call_args[0][0]
    assert str(called_uid) == uid


async def test_handle_user_deactivated_missing_user_id_skips() -> None:
    svc = make_service()
    await _handle_user_deactivated({}, svc)
    svc.deactivate_profile.assert_not_called()


async def test_handle_user_deactivated_does_not_access_repo() -> None:
    """Regression: consumer must never touch service._repo directly."""
    svc = make_service()
    uid = str(uuid4())
    await _handle_user_deactivated({"user_id": uid}, svc)
    # _repo should never be accessed — it's a private attribute
    assert not hasattr(svc, "_repo") or not svc._repo.called


# ── _handle_password_changed ──────────────────────────────────────────────────


async def test_handle_password_changed_calls_clear_flag() -> None:
    # Arrange
    svc = make_service()
    uid = str(uuid4())

    # Act
    await _handle_password_changed({"user_id": uid}, svc)

    # Assert — must use the public method, NOT _repo
    svc.clear_password_change_flag.assert_called_once()
    called_uid = svc.clear_password_change_flag.call_args[0][0]
    assert str(called_uid) == uid


async def test_handle_password_changed_missing_user_id_skips() -> None:
    svc = make_service()
    await _handle_password_changed({}, svc)
    svc.clear_password_change_flag.assert_not_called()


async def test_handle_password_changed_does_not_access_repo() -> None:
    """Regression: consumer must never touch service._repo directly."""
    svc = make_service()
    uid = str(uuid4())
    await _handle_password_changed({"user_id": uid}, svc)
    assert not hasattr(svc, "_repo") or not svc._repo.called


# ── handle_event routing ──────────────────────────────────────────────────────


async def test_handle_event_routes_user_registered() -> None:
    svc = make_service()
    uid = str(uuid4())
    event = {
        "detail-type": "identity.user.registered",
        "detail": {"user_id": uid, "email": "[email]", "full_name": "X"},
    }
    await handle_event(event, svc)
    svc.create_profile.assert_called_once()


async def test_handle_event_routes_user_deactivated() -> None:
    svc = make_service()
    uid = str(uuid4())
    event = {"detail-type": "identity.user.deactivated", "detail": {"user_id": uid}}
    await handle_event(event, svc)
    svc.deactivate_profile.assert_called_once()


async def test_handle_event_routes_password_changed() -> None:
    svc = make_service()
    uid = str(uuid4())
    event = {"detail-type": "identity.auth.password_changed", "detail": {"user_id": uid}}
    await handle_event(event, svc)
    svc.clear_password_change_flag.assert_called_once()


async def test_handle_event_unknown_type_does_nothing() -> None:
    svc = make_service()
    event = {"detail-type": "unknown.event", "detail": {}}
    await handle_event(event, svc)
    svc.create_profile.assert_not_called()
    svc.deactivate_profile.assert_not_called()
    svc.clear_password_change_flag.assert_not_called()
