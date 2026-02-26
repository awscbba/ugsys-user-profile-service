"""Unit tests for async EventBridgePublisher — TDD Task 6.1.

Written FIRST — will fail (RED) until EventBridgePublisher is migrated to aioboto3.
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from botocore.exceptions import ClientError

from src.domain.exceptions import ExternalServiceError


def _make_client_error(code: str = "InternalServerError") -> ClientError:
    return ClientError(
        error_response={"Error": {"Code": code, "Message": "Test error"}},
        operation_name="PutEvents",
    )


def _make_publisher(mock_session: Any):
    """Build EventBridgePublisher with an injected mock aioboto3 session."""

    from src.infrastructure.messaging.event_publisher import EventBridgePublisher

    return EventBridgePublisher(
        event_bus_name="ugsys-event-bus",
        region="us-east-1",
        session=mock_session,
    )


def _make_mock_session(put_events_return: Any = None, put_events_side_effect: Any = None):
    """Build a mock aioboto3 session whose events client returns the given value."""
    import aioboto3

    mock_client = AsyncMock()
    if put_events_side_effect is not None:
        mock_client.put_events.side_effect = put_events_side_effect
    else:
        mock_client.put_events.return_value = put_events_return or {
            "FailedEntryCount": 0,
            "Entries": [{"EventId": "abc-123"}],
        }

    mock_session = MagicMock(spec=aioboto3.Session)
    mock_session.client.return_value.__aenter__ = AsyncMock(return_value=mock_client)
    mock_session.client.return_value.__aexit__ = AsyncMock(return_value=False)
    return mock_session, mock_client


# ── Success path ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_publish_success_uses_async_context_manager() -> None:
    """Publisher opens client via async with session.client(...) and awaits put_events."""
    mock_session, mock_client = _make_mock_session()
    publisher = _make_publisher(mock_session)

    await publisher.publish("identity.user.registered", {"user_id": "u-1"})

    mock_session.client.assert_called_once_with("events", region_name="us-east-1")
    mock_client.put_events.assert_awaited_once()


@pytest.mark.asyncio
async def test_publish_success_logs_info() -> None:
    """On success, publisher logs at info level with detail_type and event_id."""
    import structlog

    log_entries: list[dict] = []

    def capture(logger, method, event_dict):  # type: ignore[no-untyped-def]
        log_entries.append(dict(event_dict))
        raise structlog.DropEvent()

    structlog.configure(
        processors=[capture],
        wrapper_class=structlog.BoundLogger,
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )
    try:
        mock_session, _ = _make_mock_session()
        publisher = _make_publisher(mock_session)
        await publisher.publish("identity.user.registered", {"user_id": "u-1"})
    finally:
        structlog.reset_defaults()

    info_entries = [e for e in log_entries if e.get("event") == "event.published"]
    assert len(info_entries) == 1
    assert info_entries[0]["detail_type"] == "identity.user.registered"
    assert "event_id" in info_entries[0]


# ── FailedEntryCount > 0 ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_publish_failed_entry_count_raises_external_service_error() -> None:
    """FailedEntryCount > 0 in put_events response → ExternalServiceError."""
    mock_session, _ = _make_mock_session(
        put_events_return={
            "FailedEntryCount": 1,
            "Entries": [{"ErrorCode": "InternalFailure", "ErrorMessage": "oops"}],
        }
    )
    publisher = _make_publisher(mock_session)

    with pytest.raises(ExternalServiceError) as exc_info:
        await publisher.publish("identity.user.registered", {"user_id": "u-1"})

    assert exc_info.value.user_message == "An unexpected error occurred"


# ── ClientError propagation ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_publish_client_error_raises_external_service_error() -> None:
    """put_events raises ClientError → ExternalServiceError (not ClientError)."""
    mock_session, _ = _make_mock_session(put_events_side_effect=_make_client_error())
    publisher = _make_publisher(mock_session)

    with pytest.raises(ExternalServiceError) as exc_info:
        await publisher.publish("identity.user.registered", {"user_id": "u-1"})

    assert exc_info.value.user_message == "An unexpected error occurred"


@pytest.mark.asyncio
async def test_publish_generic_exception_raises_external_service_error() -> None:
    """put_events raises generic Exception → ExternalServiceError."""
    mock_session, _ = _make_mock_session(put_events_side_effect=ConnectionError("timeout"))
    publisher = _make_publisher(mock_session)

    with pytest.raises(ExternalServiceError):
        await publisher.publish("identity.user.registered", {"user_id": "u-1"})


@pytest.mark.asyncio
async def test_publish_external_service_error_not_double_wrapped() -> None:
    """ExternalServiceError raised inside try block is re-raised directly, not wrapped again."""
    mock_session, _mock_client = _make_mock_session(
        put_events_return={
            "FailedEntryCount": 1,
            "Entries": [{"ErrorCode": "InternalFailure", "ErrorMessage": "fail"}],
        }
    )
    publisher = _make_publisher(mock_session)

    with pytest.raises(ExternalServiceError) as exc_info:
        await publisher.publish("test.event", {})

    # Should be exactly ExternalServiceError, not a subclass wrapping another
    assert type(exc_info.value) is ExternalServiceError
