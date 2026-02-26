"""Integration tests for S3AvatarStorage.

Strategy: moto's S3 handler cannot process aiobotocore's async request body
(AioAwsChunkedWrapper), so we mock the aioboto3 session/client with AsyncMock.
This tests S3AvatarStorage's logic — key construction, URL format, error
handling — without depending on moto's S3 implementation.
"""

import uuid
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

import pytest
from botocore.exceptions import ClientError

from src.infrastructure.adapters.s3_avatar_storage import S3AvatarStorage

BUCKET_NAME = "ugsys-avatars-test"
REGION = "us-east-1"


def _make_client_error(code: str) -> ClientError:
    return ClientError(
        {"Error": {"Code": code, "Message": "mocked"}},
        "operation",
    )


def _make_storage(mock_client: AsyncMock) -> S3AvatarStorage:
    """Build S3AvatarStorage with a session whose client() returns mock_client."""
    mock_session = MagicMock()

    @asynccontextmanager
    async def _client_ctx(*args, **kwargs):  # type: ignore[no-untyped-def]
        yield mock_client

    mock_session.client = _client_ctx
    return S3AvatarStorage(bucket_name=BUCKET_NAME, region=REGION, session=mock_session)


# ── 4.6.1 Upload ─────────────────────────────────────────────────────────────


async def test_upload_stores_object_and_returns_url() -> None:
    """4.6.1 upload() calls put_object with correct bucket/key and returns URL."""
    mock_client = AsyncMock()
    storage = _make_storage(mock_client)
    user_id = uuid.uuid4()

    url = await storage.upload(user_id, b"fake-image-data", "jpg")

    expected_key = f"avatars/{user_id}.jpg"
    mock_client.put_object.assert_awaited_once_with(
        Bucket=BUCKET_NAME,
        Key=expected_key,
        Body=b"fake-image-data",
    )
    assert expected_key in url
    assert BUCKET_NAME in url
    assert REGION in url


async def test_upload_url_format() -> None:
    """URL returned by upload() matches the expected S3 path-style format."""
    mock_client = AsyncMock()
    storage = _make_storage(mock_client)
    user_id = uuid.uuid4()

    url = await storage.upload(user_id, b"data", "png")

    assert url == f"https://{BUCKET_NAME}.s3.{REGION}.amazonaws.com/avatars/{user_id}.png"


# ── 4.6.3 Delete ─────────────────────────────────────────────────────────────


async def test_delete_calls_delete_object() -> None:
    """4.6.3 delete() calls delete_object with correct bucket/key."""
    mock_client = AsyncMock()
    storage = _make_storage(mock_client)
    user_id = uuid.uuid4()

    await storage.delete(user_id, "png")

    mock_client.delete_object.assert_awaited_once_with(
        Bucket=BUCKET_NAME,
        Key=f"avatars/{user_id}.png",
    )


async def test_delete_nonexistent_does_not_raise() -> None:
    """delete() silently ignores NoSuchKey ClientError."""
    mock_client = AsyncMock()
    mock_client.delete_object.side_effect = _make_client_error("NoSuchKey")
    storage = _make_storage(mock_client)

    # Should not raise
    await storage.delete(uuid.uuid4(), "jpg")


async def test_delete_other_client_error_propagates() -> None:
    """delete() re-raises ClientError codes other than NoSuchKey."""
    mock_client = AsyncMock()
    mock_client.delete_object.side_effect = _make_client_error("AccessDenied")
    storage = _make_storage(mock_client)

    with pytest.raises(ClientError) as exc_info:
        await storage.delete(uuid.uuid4(), "jpg")

    assert exc_info.value.response["Error"]["Code"] == "AccessDenied"
