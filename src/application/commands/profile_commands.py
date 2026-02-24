"""Commands for profile write operations."""

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class CreateProfileCommand:
    user_id: UUID
    email: str
    full_name: str
    phone: str = ""
    date_of_birth: str = ""
    street: str = ""
    city: str = ""
    state: str = ""
    postal_code: str = ""
    country: str = ""
    email_verified: bool = False
    require_password_change: bool = False


@dataclass(frozen=True)
class UpdateContactCommand:
    user_id: UUID
    requester_id: str  # must match user_id (self-update only)
    phone: str | None = None
    street: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str | None = None


@dataclass(frozen=True)
class UpdatePersonalCommand:
    user_id: UUID
    requester_id: str
    full_name: str | None = None
    date_of_birth: str | None = None


@dataclass(frozen=True)
class DeleteProfileCommand:
    user_id: UUID
