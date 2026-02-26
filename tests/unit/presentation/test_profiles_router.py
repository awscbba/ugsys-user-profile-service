"""Unit tests for profiles router — verifies IProfileService injection and ProfileResponse usage.

TDD: written FIRST, will fail (RED) until router is updated.
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.application.interfaces.profile_service import IProfileService
from src.domain.entities.profile import Address, UserProfile
from src.domain.value_objects.notification_preferences import NotificationPreferences
from src.presentation.api.v1.profiles import router

# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_profile(user_id=None):  # type: ignore[no-untyped-def]
    uid = user_id or uuid4()
    return UserProfile(
        user_id=uid,
        email="test@example.com",
        full_name="Test User",
        phone="",
        date_of_birth="",
        address=Address(),
        notification_preferences=NotificationPreferences(),
    )


def _make_token_service(sub: str) -> MagicMock:
    svc = MagicMock()
    svc.verify_token.return_value = {"sub": sub, "roles": ["admin"]}
    return svc


def _make_app(profile_service: IProfileService, token_service: Any) -> FastAPI:
    """Build a minimal FastAPI app with the profiles router and overridden deps."""
    from src.presentation.api.v1.profiles import get_profile_service, get_token_service

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_profile_service] = lambda: profile_service
    app.dependency_overrides[get_token_service] = lambda: token_service
    return app


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_get_profile_returns_profile_response_shape() -> None:
    """Router uses ProfileResponse.from_domain() — response has all ProfileResponse fields."""
    uid = uuid4()
    profile = _make_profile(user_id=uid)

    mock_service = AsyncMock(spec=IProfileService)
    mock_service.get_profile.return_value = profile
    token_svc = _make_token_service(sub=str(uid))

    app = _make_app(mock_service, token_svc)
    client = TestClient(app, raise_server_exceptions=True)

    resp = client.get(
        f"/api/v1/profiles/{uid}",
        headers={"Authorization": "Bearer fake-token"},
    )

    assert resp.status_code == 200
    data = resp.json()["data"]
    # ProfileResponse fields must be present
    assert data["user_id"] == str(uid)
    assert "email" in data
    assert "full_name" in data
    assert "address" in data
    assert "notification_preferences" in data
    assert "deleted_at" in data


def test_get_profile_service_dependency_accepts_iprofile_service() -> None:
    """get_profile_service() return type annotation must be IProfileService (not ProfileService)."""

    from src.presentation.api.v1.profiles import get_profile_service

    hints = get_profile_service.__annotations__
    return_type = hints.get("return")
    assert return_type is IProfileService, (
        f"get_profile_service() return type should be IProfileService, got {return_type}"
    )


def test_list_profiles_response_uses_profile_response_fields() -> None:
    """list_profiles endpoint returns data items with ProfileResponse field shape."""
    uid = uuid4()
    profile = _make_profile(user_id=uid)

    mock_service = AsyncMock(spec=IProfileService)
    mock_service.list_profiles.return_value = ([profile], 1)
    token_svc = _make_token_service(sub=str(uid))

    app = _make_app(mock_service, token_svc)
    client = TestClient(app, raise_server_exceptions=True)

    resp = client.get(
        "/api/v1/profiles/",
        headers={"Authorization": "Bearer fake-token"},
    )

    assert resp.status_code == 200
    items = resp.json()["data"]
    assert len(items) == 1
    assert "address" in items[0]
    assert "notification_preferences" in items[0]
    assert "deleted_at" in items[0]
