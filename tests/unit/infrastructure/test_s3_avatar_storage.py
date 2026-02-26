"""Exploratory + fix-checking tests for S3AvatarStorage.

Phase 1 (1.10): run on UNFIXED code — expected to FAIL.
Phase 3 (3.10.x): run on FIXED code — expected to PASS.
"""

import inspect

import src.infrastructure.adapters.s3_avatar_storage as s3_mod


class TestS3AsyncIOExploratory:
    """1.10 Assert no synchronous boto3.client("s3") calls in async methods.

    FAILS on unfixed code.
    """

    def test_1_10_no_sync_boto3_client_in_async_methods(self):
        """Assert S3AvatarStorage does NOT use boto3.client('s3') synchronously."""
        source = inspect.getsource(s3_mod)
        assert 'boto3.client("s3"' not in source and "boto3.client('s3'" not in source, (
            "Found synchronous boto3.client('s3') call — should use aioboto3"
        )


class TestS3AsyncIOFixed:
    """3.10.x — Assert aioboto3 is used, no sync boto3.client calls."""

    def test_3_10_1_uses_aioboto3_async_context_manager(self):
        """3.10.1 S3AvatarStorage uses aioboto3 async context manager."""
        source = inspect.getsource(s3_mod)
        assert "aioboto3" in source, "Expected aioboto3 import in S3AvatarStorage"
        assert "async with" in source, "Expected async with context manager"

    def test_3_10_2_no_sync_boto3_client_calls(self):
        """3.10.2 No synchronous boto3.client('s3') calls remain."""
        source = inspect.getsource(s3_mod)
        assert 'boto3.client("s3"' not in source
        assert "boto3.client('s3'" not in source
