"""Integration test fixtures — moto-based DynamoDB setup."""

import boto3
import pytest
from moto import mock_aws

from src.infrastructure.persistence.dynamodb_profile_repository import DynamoDBProfileRepository

TABLE_NAME = "ugsys-profiles-test"
REGION = "us-east-1"


@pytest.fixture(scope="function")
def aws_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure boto3 never hits real AWS during tests."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", REGION)


@pytest.fixture(scope="function")
def dynamodb_table(aws_credentials: None):  # type: ignore[no-untyped-def]
    """Create a moto DynamoDB table and yield the boto3 Table resource."""
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
    repo = DynamoDBProfileRepository(table_name=TABLE_NAME, region=REGION)
    # Point the repo's internal table reference at the already-created moto table
    repo._table = dynamodb_table
    return repo
