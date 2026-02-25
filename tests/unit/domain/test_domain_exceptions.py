"""Unit tests for domain exception hierarchy."""

from src.domain.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    DomainError,
    ExternalServiceError,
    NotFoundError,
    RepositoryError,
    ValidationError,
)


def test_domain_error_is_exception():
    err = DomainError(message="internal", user_message="safe")
    assert isinstance(err, Exception)
    assert str(err) == "internal"


def test_domain_error_defaults():
    err = DomainError(message="msg")
    assert err.user_message == "An error occurred"
    assert err.error_code == "INTERNAL_ERROR"
    assert err.additional_data == {}


def test_validation_error_code():
    err = ValidationError(message="bad input", user_message="Invalid")
    assert err.error_code == "VALIDATION_ERROR"


def test_not_found_error_code():
    err = NotFoundError(message="missing", user_message="Not found")
    assert err.error_code == "NOT_FOUND"


def test_conflict_error_code():
    err = ConflictError(message="dup", user_message="Conflict")
    assert err.error_code == "CONFLICT"


def test_authorization_error_code():
    err = AuthorizationError(message="denied", user_message="Access denied")
    assert err.error_code == "FORBIDDEN"


def test_authentication_error_code():
    err = AuthenticationError(message="bad token", user_message="Unauthorized")
    assert err.error_code == "AUTHENTICATION_FAILED"


def test_repository_error_code():
    err = RepositoryError(message="db fail", user_message="Error")
    assert err.error_code == "REPOSITORY_ERROR"


def test_external_service_error_code():
    err = ExternalServiceError(message="s3 fail", user_message="Unavailable")
    assert err.error_code == "EXTERNAL_SERVICE_ERROR"


def test_user_message_never_equals_message():
    err = ValidationError(message="internal detail", user_message="Safe message")
    assert err.message != err.user_message
