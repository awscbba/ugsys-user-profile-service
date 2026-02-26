"""HTTP endpoint integration tests — profile CRUD flow.

Strategy:
    - Build a minimal FastAPI app with the real profiles router
    - Wire a real DynamoDBProfileRepository backed by moto
    - Mock token_service (no real JWT needed) and avatar_storage (AsyncMock)
    - Use httpx.AsyncClient(transport=ASGITransport(app)) for async HTTP calls

Note: The moto/aiobotocore compatibility patch is applied at module load in
conftest.py (same package), so it is already active when these tests run.
"""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import boto3
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from moto import mock_aws

from src.application.commands.profile_commands import CreateProfileCommand
from src.application.services.profile_service import ProfileService
from src.domain.exceptions import DomainError
from src.domain.repositories.avatar_storage import AvatarStorage
from src.infrastructure.persistence.dynamodb_profile_repository import (
    DynamoDBProfileRepository,
)
from src.presentation.api.v1 import health, profiles
from src.presentation.api.v1.profiles import get_profile_service, get_token_service
from src.presentation.middleware.correlation_id import CorrelationIdMiddleware
from src.presentation.middleware.exception_handler import (
    domain_exception_handler,
    unhandled_exception_handler,
)
from src.presentation.middleware.rate_limiting import RateLimitMiddleware
from src.presentation.middleware.security_headers import SecurityHeadersMiddleware

TABLE_NAME = "ugsys-profiles-test"
REGION = "us-east-1"


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_token_service(sub: str, roles: list[str] | None = None) -> MagicMock:
    svc = MagicMock()
    svc.verify_token.return_value = {"sub": sub, "roles": roles or []}
    return svc


def _make_admin_token_service(sub: str) -> MagicMock:
    return _make_token_service(sub=sub, roles=["admin"])


def _make_avatar_storage() -> AsyncMock:
    storage = AsyncMock(spec=AvatarStorage)
    storage.upload.return_value = "https://bucket.s3.us-east-1.amazonaws.com/avatars/test.jpg"
    return storage


def _build_app(
    repo: DynamoDBProfileRepository,
    token_service: MagicMock,
    avatar_storage: AvatarStorage | None = None,
    rate_limit: int = 60,
) -> FastAPI:
    """Build a minimal app wired to the given repo and mocked token service."""
    app = FastAPI()
    app.add_middleware(CorrelationIdMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RateLimitMiddleware, rate_limit=rate_limit)
    app.add_exception_handler(DomainError, domain_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unhandled_exception_handler)

    profile_service = ProfileService(
        profile_repo=repo,
        avatar_storage=avatar_storage,
    )

    app.dependency_overrides[get_profile_service] = lambda: profile_service
    app.dependency_overrides[get_token_service] = lambda: token_service

    app.include_router(health.router)
    app.include_router(profiles.router, prefix="/api/v1")
    return app


@asynccontextmanager
async def _client(app: FastAPI):  # type: ignore[no-untyped-def]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture()
def moto_table(aws_credentials: None):  # type: ignore[no-untyped-def]
    """Spin up a moto DynamoDB table for the flow tests."""
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
        yield


@pytest.fixture()
def repo(moto_table: None) -> DynamoDBProfileRepository:  # type: ignore[no-untyped-def]
    return DynamoDBProfileRepository(table_name=TABLE_NAME, region=REGION)


# ── 4.7.1  GET /api/v1/profiles/{id} returns 200 ─────────────────────────────


async def test_get_profile_returns_200(repo: DynamoDBProfileRepository) -> None:
    """4.7.1 GET /api/v1/profiles/{id} returns 200 with profile data."""
    uid = uuid4()
    token_svc = _make_token_service(sub=str(uid))
    app = _build_app(repo, token_svc)

    # Seed profile directly via service
    svc = ProfileService(profile_repo=repo)
    await svc.create_profile(
        CreateProfileCommand(user_id=uid, email="[email]", full_name="Test User")
    )

    async with _client(app) as c:
        resp = await c.get(
            f"/api/v1/profiles/{uid}",
            headers={"Authorization": "Bearer fake.eyJzdWIiOiJ0ZXN0In0.sig"},
        )

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["user_id"] == str(uid)
    assert data["email"] == "[email]"
    assert data["full_name"] == "Test User"


# ── 4.7.2  Profile creation via service + GET verifies persistence ────────────


async def test_create_profile_persists_and_get_returns_it(
    repo: DynamoDBProfileRepository,
) -> None:
    """4.7.2 Creating a profile via the service persists it; GET returns it."""
    uid = uuid4()
    token_svc = _make_token_service(sub=str(uid))
    app = _build_app(repo, token_svc)

    svc = ProfileService(profile_repo=repo)
    created = await svc.create_profile(
        CreateProfileCommand(
            user_id=uid,
            email="[email]",
            full_name="Integration User",
            phone="+591 70000001",
        )
    )
    assert created.user_id == uid

    async with _client(app) as c:
        resp = await c.get(
            f"/api/v1/profiles/{uid}",
            headers={"Authorization": "Bearer fake.eyJzdWIiOiJ0ZXN0In0.sig"},
        )

    assert resp.status_code == 200
    assert resp.json()["data"]["full_name"] == "Integration User"


# ── 4.7.3  PATCH /api/v1/profiles/{id}/contact returns updated data ──────────


async def test_update_contact_returns_updated_profile(
    repo: DynamoDBProfileRepository,
) -> None:
    """4.7.3 PATCH /api/v1/profiles/{id}/contact returns updated profile data."""
    uid = uuid4()
    token_svc = _make_token_service(sub=str(uid))
    app = _build_app(repo, token_svc)

    svc = ProfileService(profile_repo=repo)
    await svc.create_profile(CreateProfileCommand(user_id=uid, email="[email]", full_name="User"))

    async with _client(app) as c:
        resp = await c.patch(
            f"/api/v1/profiles/{uid}/contact",
            json={"phone": "+591 70000099"},
            headers={"Authorization": "Bearer fake.eyJzdWIiOiJ0ZXN0In0.sig"},
        )

    assert resp.status_code == 200
    assert resp.json()["data"]["phone"] == "+591 70000099"


# ── 4.7.4  DELETE /api/v1/profiles/{id} returns 204 (soft-delete, admin) ─────


async def test_soft_delete_profile_returns_204(
    repo: DynamoDBProfileRepository,
) -> None:
    """4.7.4 DELETE /api/v1/profiles/{id} returns 204 (admin soft-delete)."""
    uid = uuid4()
    admin_id = str(uuid4())
    token_svc = _make_admin_token_service(sub=admin_id)
    app = _build_app(repo, token_svc)

    svc = ProfileService(profile_repo=repo)
    await svc.create_profile(
        CreateProfileCommand(user_id=uid, email="[email]", full_name="To Delete")
    )

    async with _client(app) as c:
        resp = await c.delete(
            f"/api/v1/profiles/{uid}",
            headers={"Authorization": "Bearer fake.eyJzdWIiOiJ0ZXN0In0.sig"},
        )

    assert resp.status_code == 204


# ── 4.7.5  GET /api/v1/profiles/{id} for missing profile returns 404 ─────────


async def test_get_missing_profile_returns_404(
    repo: DynamoDBProfileRepository,
) -> None:
    """4.7.5 GET /api/v1/profiles/{id} for a non-existent profile returns 404."""
    uid = uuid4()
    token_svc = _make_admin_token_service(sub=str(uid))
    app = _build_app(repo, token_svc)

    async with _client(app) as c:
        resp = await c.get(
            f"/api/v1/profiles/{uid}",
            headers={"Authorization": "Bearer fake.eyJzdWIiOiJ0ZXN0In0.sig"},
        )

    assert resp.status_code == 404
    assert resp.json()["error"]["message"] == "Profile not found"


# ── 4.7.6  Avatar upload stores in S3 and returns avatar URL ─────────────────


async def test_avatar_upload_returns_avatar_url(
    repo: DynamoDBProfileRepository,
) -> None:
    """4.7.6 Avatar upload stores in S3 and returns avatar URL in profile data."""
    uid = uuid4()
    token_svc = _make_token_service(sub=str(uid))
    avatar_storage = _make_avatar_storage()
    app = _build_app(repo, token_svc, avatar_storage=avatar_storage)

    svc = ProfileService(profile_repo=repo)
    await svc.create_profile(
        CreateProfileCommand(user_id=uid, email="[email]", full_name="Avatar User")
    )

    async with _client(app) as c:
        resp = await c.post(
            f"/api/v1/profiles/{uid}/avatar",
            files={"file": ("avatar.jpg", b"fake-image-bytes", "image/jpeg")},
            headers={"Authorization": "Bearer fake.eyJzdWIiOiJ0ZXN0In0.sig"},
        )

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["avatar_url"] is not None
    assert "amazonaws.com" in data["avatar_url"]
    avatar_storage.upload.assert_awaited_once()


# ── 4.7.7  GET /health returns 200 without authentication ────────────────────


async def test_health_returns_200_without_auth(
    repo: DynamoDBProfileRepository,
) -> None:
    """4.7.7 GET /health returns 200 without any authentication header."""
    token_svc = _make_token_service(sub="nobody")
    app = _build_app(repo, token_svc)

    async with _client(app) as c:
        resp = await c.get("/health")

    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


# ── 4.7.8  Requests exceeding rate limit return 429 ──────────────────────────


async def test_rate_limit_exceeded_returns_429(
    repo: DynamoDBProfileRepository,
) -> None:
    """4.7.8 Requests exceeding 60 req/min return 429 with Retry-After header."""
    uid = uuid4()
    token_svc = _make_token_service(sub=str(uid))
    # Set rate_limit=1 so the second request triggers 429
    app = _build_app(repo, token_svc, rate_limit=1)

    async with _client(app) as c:
        first = await c.get(
            "/health",
            headers={"Authorization": "Bearer fake.eyJzdWIiOiJ0ZXN0In0.sig"},
        )
        second = await c.get(
            "/health",
            headers={"Authorization": "Bearer fake.eyJzdWIiOiJ0ZXN0In0.sig"},
        )

    assert first.status_code == 200
    assert second.status_code == 429
    assert "Retry-After" in second.headers
