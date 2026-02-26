"""Exploratory + fix-checking + preservation tests for DynamoDBProfileRepository.

Phase 1 (1.3.x, 1.4): run on UNFIXED code — expected to FAIL.
Phase 3 (3.3.x, 3.4, 3.5.x): run on FIXED code — expected to PASS.
Phase 4 (4.4): preservation PBT — expected to PASS on fixed code.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, ClassVar
from unittest.mock import AsyncMock, MagicMock

import pytest
from botocore.exceptions import ClientError
from hypothesis import given
from hypothesis import settings as hyp_settings
from hypothesis import strategies as st

from src.domain.entities.profile import Address, UserProfile
from src.domain.exceptions import NotFoundError, RepositoryError
from src.domain.value_objects.notification_preferences import NotificationPreferences

# ── Helpers ───────────────────────────────────────────────────────────────────


def make_profile(**kwargs: Any) -> UserProfile:
    defaults: dict[str, Any] = {
        "user_id": uuid.uuid4(),
        "email": "test@example.com",
        "full_name": "Test User",
        "phone": "+591 70000000",
        "date_of_birth": "1990-01-01",
        "address": Address(
            street="Calle 1", city="Cochabamba", state="CB", postal_code="0000", country="BO"
        ),
        "email_verified": True,
        "require_password_change": False,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
        "notification_preferences": NotificationPreferences(),
        "language": "es",
        "timezone": "America/La_Paz",
    }
    defaults.update(kwargs)
    return UserProfile(**defaults)


def make_client_error(code: str = "InternalServerError") -> ClientError:
    return ClientError(
        error_response={"Error": {"Code": code, "Message": "Test error"}},
        operation_name="TestOperation",
    )


def make_conditional_check_error() -> ClientError:
    return make_client_error("ConditionalCheckFailedException")


# ── Phase 1: Exploratory tests (expected to FAIL on unfixed code) ─────────────


class TestClientErrorLeaksExploratory:
    """1.3.x — ClientError should be wrapped as RepositoryError (FAILS on unfixed code)."""

    def _make_repo_with_mock_client(self, mock_client: AsyncMock):
        """Helper: build a repo wired to the given async mock client."""
        import aioboto3

        from src.infrastructure.persistence.dynamodb_profile_repository import (
            DynamoDBProfileRepository,
        )

        mock_session = MagicMock(spec=aioboto3.Session)
        mock_session.client.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_session.client.return_value.__aexit__ = AsyncMock(return_value=False)
        return DynamoDBProfileRepository(
            table_name="test-table",
            region="us-east-1",
            session=mock_session,
        )

    def test_1_3_1_put_item_client_error_raises_repository_error(self):
        """1.3.1 Mock put_item to raise ClientError — assert RepositoryError raised."""
        import asyncio

        mock_client = AsyncMock()
        mock_client.put_item.side_effect = make_client_error()
        repo = self._make_repo_with_mock_client(mock_client)

        profile = make_profile()
        with pytest.raises(RepositoryError):
            asyncio.run(repo.save(profile))

    def test_1_3_2_get_item_client_error_raises_repository_error(self):
        """1.3.2 Mock get_item to raise ClientError — assert RepositoryError raised."""
        import asyncio

        mock_client = AsyncMock()
        mock_client.get_item.side_effect = make_client_error()
        repo = self._make_repo_with_mock_client(mock_client)

        with pytest.raises(RepositoryError):
            asyncio.run(repo.find_by_user_id(uuid.uuid4()))

    def test_1_3_3_scan_client_error_raises_repository_error(self):
        """1.3.3 Mock scan to raise ClientError — assert RepositoryError raised."""
        import asyncio

        mock_client = AsyncMock()
        mock_client.scan.side_effect = make_client_error()
        repo = self._make_repo_with_mock_client(mock_client)

        with pytest.raises(RepositoryError):
            asyncio.run(repo.list_profiles(1, 10))

    def test_1_3_4_delete_item_client_error_raises_repository_error(self):
        """1.3.4 Mock delete_item to raise ClientError — assert RepositoryError raised."""
        import asyncio

        mock_client = AsyncMock()
        mock_client.delete_item.side_effect = make_client_error()
        repo = self._make_repo_with_mock_client(mock_client)

        with pytest.raises(RepositoryError):
            asyncio.run(repo.delete(uuid.uuid4()))

    def test_1_3_5_save_conditional_check_raises_repository_error(self):
        """1.3.5 ConditionalCheckFailedException in save() → RepositoryError(REPOSITORY_ERROR)."""
        import asyncio

        mock_client = AsyncMock()
        mock_client.put_item.side_effect = make_conditional_check_error()
        repo = self._make_repo_with_mock_client(mock_client)

        profile = make_profile()
        with pytest.raises(RepositoryError) as exc_info:
            asyncio.run(repo.save(profile))
        assert exc_info.value.error_code == "REPOSITORY_ERROR"

    def test_1_3_6_update_conditional_check_raises_not_found_error(self):
        """1.3.6 ConditionalCheckFailedException in update() → NotFoundError.

        user_message='Profile not found'
        """
        import asyncio

        mock_client = AsyncMock()
        mock_client.put_item.side_effect = make_conditional_check_error()
        repo = self._make_repo_with_mock_client(mock_client)

        profile = make_profile()
        with pytest.raises(NotFoundError) as exc_info:
            asyncio.run(repo.update(profile))
        assert exc_info.value.user_message == "Profile not found"


# ── Phase 1: PBT (1.4) ────────────────────────────────────────────────────────


class TestClientErrorPBTExploratory:
    """1.4 PBT: Any ClientError code → RepositoryError.

    Or NotFoundError for update ConditionalCheck.
    **Validates: Requirements 2.8, 2.9, 2.10**
    """

    _ERROR_CODES: ClassVar[list[str]] = [
        "InternalServerError",
        "ProvisionedThroughputExceededException",
        "ResourceNotFoundException",
        "RequestLimitExceeded",
        "ServiceUnavailable",
        "ThrottlingException",
        "ValidationException",
        "AccessDeniedException",
    ]

    @given(error_code=st.sampled_from(_ERROR_CODES))
    @hyp_settings(max_examples=8)
    def test_1_4_any_client_error_on_get_item_raises_repository_error(
        self, error_code: str
    ) -> None:
        """For any ClientError code on get_item, RepositoryError is raised."""
        import asyncio

        import aioboto3

        from src.infrastructure.persistence.dynamodb_profile_repository import (
            DynamoDBProfileRepository,
        )

        mock_session = MagicMock(spec=aioboto3.Session)
        mock_client = AsyncMock()
        mock_client.get_item.side_effect = make_client_error(error_code)
        mock_session.client.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_session.client.return_value.__aexit__ = AsyncMock(return_value=False)
        repo = DynamoDBProfileRepository(
            table_name="test-table",
            region="us-east-1",
            session=mock_session,
        )

        with pytest.raises(RepositoryError):
            asyncio.run(repo.find_by_user_id(uuid.uuid4()))


# ── Phase 1: Gap 3 exploratory (1.5) ─────────────────────────────────────────


class TestAsyncIODynamoDBExploratory:
    """1.5 Assert no synchronous boto3.resource calls in async methods (FAILS on unfixed code)."""

    def test_1_5_no_sync_boto3_resource_in_async_methods(self):
        """Assert DynamoDBProfileRepository does NOT use boto3.resource synchronously."""
        import inspect

        import src.infrastructure.persistence.dynamodb_profile_repository as mod

        source = inspect.getsource(mod)
        assert (
            'boto3.resource("dynamodb"' not in source and "boto3.resource('dynamodb'" not in source
        ), "Found synchronous boto3.resource('dynamodb') call — should use aioboto3"


# ── Phase 3: Fix-checking tests (expected to PASS on fixed code) ──────────────


class TestClientErrorWrappingFixed:
    """3.3.x — ClientError wrapping works correctly on fixed code."""

    @pytest.fixture
    def repo_with_mock_client(self):
        """Create repo with a mock async DynamoDB client."""
        import aioboto3

        from src.infrastructure.persistence.dynamodb_profile_repository import (
            DynamoDBProfileRepository,
        )

        mock_session = MagicMock(spec=aioboto3.Session)
        mock_client = AsyncMock()
        mock_session.client.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_session.client.return_value.__aexit__ = AsyncMock(return_value=False)
        repo = DynamoDBProfileRepository(
            table_name="test-table",
            region="us-east-1",
            session=mock_session,
        )
        return repo, mock_client

    @pytest.mark.asyncio
    async def test_3_3_1_put_item_client_error_raises_repository_error_with_safe_message(
        self, repo_with_mock_client
    ):
        """3.3.1 put_item ClientError → RepositoryError with safe user_message."""
        repo, mock_client = repo_with_mock_client
        mock_client.put_item.side_effect = make_client_error()
        profile = make_profile()
        with pytest.raises(RepositoryError) as exc_info:
            await repo.save(profile)
        assert exc_info.value.user_message == "An unexpected error occurred"

    @pytest.mark.asyncio
    async def test_3_3_1_get_item_client_error_raises_repository_error(self, repo_with_mock_client):
        """3.3.1 get_item ClientError → RepositoryError."""
        repo, mock_client = repo_with_mock_client
        mock_client.get_item.side_effect = make_client_error()
        with pytest.raises(RepositoryError):
            await repo.find_by_user_id(uuid.uuid4())

    @pytest.mark.asyncio
    async def test_3_3_1_scan_client_error_raises_repository_error(self, repo_with_mock_client):
        """3.3.1 scan ClientError → RepositoryError."""
        repo, mock_client = repo_with_mock_client
        mock_client.scan.side_effect = make_client_error()
        with pytest.raises(RepositoryError):
            await repo.list_profiles(1, 10)

    @pytest.mark.asyncio
    async def test_3_3_1_delete_item_client_error_raises_repository_error(
        self, repo_with_mock_client
    ):
        """3.3.1 delete_item ClientError → RepositoryError."""
        repo, mock_client = repo_with_mock_client
        mock_client.delete_item.side_effect = make_client_error()
        with pytest.raises(RepositoryError):
            await repo.delete(uuid.uuid4())

    @pytest.mark.asyncio
    async def test_3_3_2_save_conditional_check_raises_repository_error(
        self, repo_with_mock_client
    ):
        """3.3.2 ConditionalCheckFailedException in save() → RepositoryError(REPOSITORY_ERROR)."""
        repo, mock_client = repo_with_mock_client
        mock_client.put_item.side_effect = make_conditional_check_error()
        profile = make_profile()
        with pytest.raises(RepositoryError) as exc_info:
            await repo.save(profile)
        assert exc_info.value.error_code == "REPOSITORY_ERROR"

    @pytest.mark.asyncio
    async def test_3_3_3_update_conditional_check_raises_not_found_error(
        self, repo_with_mock_client
    ):
        """3.3.3 ConditionalCheckFailedException in update() → NotFoundError.

        NOT_FOUND, 'Profile not found'
        """
        repo, mock_client = repo_with_mock_client
        mock_client.put_item.side_effect = make_conditional_check_error()
        profile = make_profile()
        with pytest.raises(NotFoundError) as exc_info:
            await repo.update(profile)
        assert exc_info.value.error_code == "NOT_FOUND"
        assert exc_info.value.user_message == "Profile not found"


# ── Phase 3: PBT (3.4) ────────────────────────────────────────────────────────


class TestClientErrorPBTFixed:
    """3.4 PBT: Any ClientError code → RepositoryError on fixed code.

    **Validates: Requirements 2.8, 2.9, 2.10**
    """

    _ERROR_CODES: ClassVar[list[str]] = [
        "InternalServerError",
        "ProvisionedThroughputExceededException",
        "ResourceNotFoundException",
        "RequestLimitExceeded",
        "ServiceUnavailable",
        "ThrottlingException",
        "ValidationException",
        "AccessDeniedException",
    ]

    @given(error_code=st.sampled_from(_ERROR_CODES))
    @hyp_settings(max_examples=8)
    def test_3_4_any_client_error_raises_repository_error(self, error_code: str) -> None:
        """For any ClientError code on get_item, RepositoryError is raised (fixed code)."""
        import aioboto3

        from src.infrastructure.persistence.dynamodb_profile_repository import (
            DynamoDBProfileRepository,
        )

        mock_session = MagicMock(spec=aioboto3.Session)
        mock_client = AsyncMock()
        mock_client.get_item.side_effect = make_client_error(error_code)
        mock_session.client.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_session.client.return_value.__aexit__ = AsyncMock(return_value=False)
        repo = DynamoDBProfileRepository(
            table_name="test-table",
            region="us-east-1",
            session=mock_session,
        )

        import asyncio

        with pytest.raises(RepositoryError):
            asyncio.run(repo.find_by_user_id(uuid.uuid4()))


# ── Phase 3: Async I/O fix-checking (3.5.x) ──────────────────────────────────


class TestAsyncIODynamoDBFixed:
    """3.5.x — Assert aioboto3 is used, no sync boto3.resource calls."""

    def test_3_5_1_uses_aioboto3_async_context_manager(self):
        """3.5.1 DynamoDBProfileRepository uses aioboto3 async context manager."""
        import inspect

        import src.infrastructure.persistence.dynamodb_profile_repository as mod

        source = inspect.getsource(mod)
        assert "aioboto3" in source, "Expected aioboto3 import in repository"
        assert "async with" in source, "Expected async with context manager"

    def test_3_5_2_no_sync_boto3_resource_calls(self):
        """3.5.2 No synchronous boto3.resource() calls remain."""
        import inspect

        import src.infrastructure.persistence.dynamodb_profile_repository as mod

        source = inspect.getsource(mod)
        assert 'boto3.resource("dynamodb"' not in source
        assert "boto3.resource('dynamodb'" not in source


# ── Phase 4: Preservation PBT (4.4) ──────────────────────────────────────────


class TestRoundTripPreservation:
    """4.4 PBT: _to_item/_from_item round-trip preserves domain entity.

    **Validates: Requirements 3.9**
    """

    @given(
        full_name=st.text(min_size=1, max_size=50),
        email=st.emails(),
        language=st.sampled_from(["es", "en", "pt"]),
        timezone=st.sampled_from(["America/La_Paz", "UTC", "America/New_York"]),
        bio=st.one_of(st.none(), st.text(max_size=100)),
        display_name=st.one_of(st.none(), st.text(max_size=50)),
    )
    @hyp_settings(max_examples=20)
    def test_4_4_to_item_from_item_round_trip(
        self,
        full_name: str,
        email: str,
        language: str,
        timezone: str,
        bio: str | None,
        display_name: str | None,
    ) -> None:
        """For any valid profile payload, _to_item/_from_item round-trip returns same entity."""
        from src.infrastructure.persistence.dynamodb_profile_repository import (
            DynamoDBProfileRepository,
        )

        profile = make_profile(
            full_name=full_name,
            email=email,
            language=language,
            timezone=timezone,
            bio=bio,
            display_name=display_name,
        )
        item = DynamoDBProfileRepository._to_item(profile)
        restored = DynamoDBProfileRepository._from_item(item)

        assert restored.user_id == profile.user_id
        assert restored.email == profile.email
        assert restored.full_name == profile.full_name
        assert restored.language == profile.language
        assert restored.timezone == profile.timezone
        assert restored.bio == profile.bio
        assert restored.display_name == profile.display_name
