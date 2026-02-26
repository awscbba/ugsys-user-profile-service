"""Integration test fixtures — moto-based DynamoDB setup.

Compatibility note:
    moto intercepts at the botocore HTTP layer and returns synchronous
    AWSResponse objects, but aiobotocore awaits `http_response.content`.

    Strategy:
    AWSResponse.content is patched once at module load to return an
    _AwaitableBytes instance — a bytes subclass that is also awaitable.
    This satisfies both callers simultaneously:
      - sync botocore parsers call .decode() directly on the bytes value ✓
      - aiobotocore does `body = await response.content` ✓

    No per-test swap needed; the patch is safe for the full session.
"""

import boto3
import pytest
from botocore.awsrequest import AWSResponse
from moto import mock_aws

from src.infrastructure.persistence.dynamodb_profile_repository import DynamoDBProfileRepository

TABLE_NAME = "ugsys-profiles-test"
REGION = "us-east-1"

# ── moto / aiobotocore compatibility patch ────────────────────────────────────


class _AwaitableBytes(bytes):
    """bytes subclass that is also awaitable.

    Sync callers (botocore parsers) use it as plain bytes via .decode() etc.
    Async callers (aiobotocore) can `await` it and get the same bytes back.

    __await__ must be a generator function that returns `self` (bytes).
    The `yield` is never reached — it just makes CPython treat this as a
    generator-based coroutine. The `return self` raises StopIteration(self),
    which is how `await` resolves the value.
    """

    def __await__(self):  # type: ignore[override]
        return self
        yield  # noqa: unreachable — makes this a generator function


_original_content_fget = AWSResponse.content.fget  # type: ignore[attr-defined]


def _awaitable_content(self: AWSResponse) -> _AwaitableBytes:  # type: ignore[type-arg]
    raw: bytes = _original_content_fget(self)  # type: ignore[arg-type]
    return _AwaitableBytes(raw)


AWSResponse.content = property(_awaitable_content)  # type: ignore[assignment]

# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture(scope="function")
def aws_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure boto3/aioboto3 never hits real AWS during tests."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", REGION)


@pytest.fixture(scope="function")
def dynamodb_table(aws_credentials: None):  # type: ignore[no-untyped-def]
    """Create a moto DynamoDB table and yield the boto3 Table resource for direct writes."""
    with mock_aws():
        client = boto3.client("dynamodb", region_name=REGION)
        client.create_table(
            TableName=TABLE_NAME,
            KeySchema=[
                {"AttributeName": "pk", "KeyType": "HASH"},
                {"AttributeName": "sk", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "pk", "AttributeType": "S"},
                {"AttributeName": "sk", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        yield boto3.resource("dynamodb", region_name=REGION).Table(TABLE_NAME)


@pytest.fixture(scope="function")
def profile_repo(dynamodb_table):  # type: ignore[no-untyped-def]
    """Return a DynamoDBProfileRepository wired to the moto table."""
    return DynamoDBProfileRepository(table_name=TABLE_NAME, region=REGION)
