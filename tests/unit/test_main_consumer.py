"""Unit tests for main_consumer Lambda handler — TDD Task 7.1.

Written FIRST — will fail (RED) until src/main_consumer.py is implemented.
"""

import asyncio
import warnings
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest


def _make_event(detail_type: str = "identity.user.registered", payload: dict | None = None) -> dict:
    return {
        "detail-type": detail_type,
        "detail": {
            "payload": payload or {"user_id": "u-1", "email": "a@b.com", "full_name": "A B"},
        },
    }


# ── Success path ──────────────────────────────────────────────────────────────


def test_lambda_handler_returns_200_on_success() -> None:
    """handle_event completes normally → {"statusCode": 200, "body": "OK"}."""
    from src.main_consumer import lambda_handler

    with patch("src.main_consumer.asyncio.run") as mock_run:
        mock_run.return_value = None
        result = lambda_handler(_make_event(), {})

    assert result == {"statusCode": 200, "body": "OK"}


# ── Failure path ──────────────────────────────────────────────────────────────


def test_lambda_handler_reraises_on_failure() -> None:
    """handle_event raises → lambda_handler re-raises (Lambda marks invocation failed)."""
    from src.main_consumer import lambda_handler

    with (
        patch("src.main_consumer.asyncio.run", side_effect=RuntimeError("crash")),
        pytest.raises(RuntimeError, match="crash"),
    ):
        lambda_handler(_make_event(), {})


def test_lambda_handler_does_not_return_200_on_failure() -> None:
    """On exception, lambda_handler must not swallow and return 200."""
    from src.main_consumer import lambda_handler

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        with (
            patch("src.main_consumer.asyncio.run", side_effect=ValueError("bad")),
            pytest.raises(ValueError),
        ):
            lambda_handler(_make_event(), {})


# ── Envelope extraction ───────────────────────────────────────────────────────


def _run_and_capture(coro: Any) -> None:
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(coro)
    finally:
        loop.close()


def test_lambda_handler_extracts_detail_type_from_envelope() -> None:
    """detail-type is extracted from the outer EventBridge envelope."""
    from src.main_consumer import lambda_handler

    event = _make_event(detail_type="identity.user.deactivated")

    with (
        patch("src.main_consumer.handle_event", new_callable=AsyncMock) as mock_handle,
        patch("src.main_consumer.asyncio.run", side_effect=_run_and_capture),
    ):
        lambda_handler(event, {})
        passed_event = mock_handle.call_args[0][0]
        assert passed_event["detail-type"] == "identity.user.deactivated"


def test_lambda_handler_passes_payload_as_detail() -> None:
    """Payload from event['detail']['payload'] is passed as detail to handle_event."""
    from src.main_consumer import lambda_handler

    payload = {"user_id": "u-42", "email": "x@y.com", "full_name": "X Y"}
    event = _make_event(payload=payload)

    with (
        patch("src.main_consumer.handle_event", new_callable=AsyncMock) as mock_handle,
        patch("src.main_consumer.asyncio.run", side_effect=_run_and_capture),
    ):
        lambda_handler(event, {})
        passed_event = mock_handle.call_args[0][0]
        assert passed_event["detail"] == payload
