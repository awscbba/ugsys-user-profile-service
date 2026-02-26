"""Unit tests for IProfileService ABC — interface compliance.

TDD: written FIRST, will fail (RED) until IProfileService is implemented.
"""

from unittest.mock import AsyncMock

import pytest

from src.application.interfaces.profile_service import IProfileService
from src.application.services.profile_service import ProfileService
from src.domain.repositories.avatar_storage import AvatarStorage
from src.domain.repositories.event_publisher import EventPublisher
from src.domain.repositories.profile_repository import ProfileRepository

# ── ABC enforcement ───────────────────────────────────────────────────────────


def test_incomplete_stub_raises_type_error() -> None:
    """A class missing abstract methods cannot be instantiated."""

    class IncompleteService(IProfileService):
        pass  # implements nothing

    with pytest.raises(TypeError):
        IncompleteService()  # type: ignore[abstract]


def test_complete_stub_does_not_raise() -> None:
    """A class implementing all abstract methods can be instantiated."""

    class CompleteStub(IProfileService):
        async def get_profile(self, query):  # type: ignore[override]
            ...

        async def create_profile(self, command):  # type: ignore[override]
            ...

        async def update_contact(self, command):  # type: ignore[override]
            ...

        async def update_personal(self, command):  # type: ignore[override]
            ...

        async def delete_profile(self, command):  # type: ignore[override]
            ...

        async def upload_avatar(self, command):  # type: ignore[override]
            ...

        async def delete_avatar(self, command):  # type: ignore[override]
            ...

        async def update_preferences(self, command):  # type: ignore[override]
            ...

        async def update_display(self, command):  # type: ignore[override]
            ...

        async def list_profiles(self, query):  # type: ignore[override]
            ...

        async def soft_delete_profile(self, command):  # type: ignore[override]
            ...

        async def get_profile_by_id(self, user_id):  # type: ignore[override]
            ...

        async def deactivate_profile(self, user_id):  # type: ignore[override]
            ...

        async def clear_password_change_flag(self, user_id):  # type: ignore[override]
            ...

    stub = CompleteStub()
    assert isinstance(stub, IProfileService)


# ── ProfileService satisfies IProfileService ─────────────────────────────────


def test_profile_service_is_instance_of_iprofile_service() -> None:
    """Task 3.1 — ProfileService must satisfy IProfileService."""
    repo = AsyncMock(spec=ProfileRepository)
    events = AsyncMock(spec=EventPublisher)
    storage = AsyncMock(spec=AvatarStorage)

    service = ProfileService(profile_repo=repo, event_publisher=events, avatar_storage=storage)

    assert isinstance(service, IProfileService)
