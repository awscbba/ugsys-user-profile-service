"""UserProfile entity — demographic and contact data for a platform user."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID


@dataclass
class Address:
    street: str = ""
    city: str = ""
    state: str = ""
    postal_code: str = ""
    country: str = ""


@dataclass
class UserProfile:
    """
    Canonical store for all personal/demographic data.

    Keyed by user_id — the same UUID issued by identity-manager.
    Other services (omnichannel, mass-messaging, projects-registry) query
    this service when they need phone, dateOfBirth, address, etc.
    """

    user_id: UUID
    email: str  # denormalized from identity-manager for convenience
    full_name: str
    phone: str = ""
    date_of_birth: str = ""  # YYYY-MM-DD
    address: Address = field(default_factory=Address)
    email_verified: bool = False
    require_password_change: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    # Audit — set during migration from Registry
    migrated_from: str | None = None
    migrated_at: datetime | None = None

    def update_contact(
        self,
        phone: str | None = None,
        address: Address | None = None,
    ) -> None:
        if phone is not None:
            self.phone = phone
        if address is not None:
            self.address = address
        self.updated_at = datetime.now(UTC)

    def update_personal(
        self,
        full_name: str | None = None,
        date_of_birth: str | None = None,
    ) -> None:
        if full_name is not None:
            self.full_name = full_name
        if date_of_birth is not None:
            self.date_of_birth = date_of_birth
        self.updated_at = datetime.now(UTC)

    def mark_email_verified(self) -> None:
        self.email_verified = True
        self.updated_at = datetime.now(UTC)

    def clear_password_change_flag(self) -> None:
        self.require_password_change = False
        self.updated_at = datetime.now(UTC)
