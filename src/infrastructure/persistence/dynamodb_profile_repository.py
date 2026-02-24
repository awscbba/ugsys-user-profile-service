"""DynamoDB adapter implementing ProfileRepository port."""

from datetime import datetime
from uuid import UUID

import boto3
import structlog

from src.domain.entities.profile import Address, UserProfile
from src.domain.repositories.profile_repository import ProfileRepository

logger = structlog.get_logger()


class DynamoDBProfileRepository(ProfileRepository):
    def __init__(self, table_name: str, region: str = "us-east-1") -> None:
        self._table = boto3.resource("dynamodb", region_name=region).Table(table_name)

    async def save(self, profile: UserProfile) -> UserProfile:
        self._table.put_item(Item=self._to_item(profile))
        logger.info("dynamodb.profile.saved", user_id=str(profile.user_id))
        return profile

    async def update(self, profile: UserProfile) -> UserProfile:
        self._table.put_item(Item=self._to_item(profile))
        logger.info("dynamodb.profile.updated", user_id=str(profile.user_id))
        return profile

    async def find_by_user_id(self, user_id: UUID) -> UserProfile | None:
        resp = self._table.get_item(Key={"pk": f"PROFILE#{user_id}", "sk": "PROFILE"})
        item = resp.get("Item")
        return self._from_item(item) if item else None

    async def delete(self, user_id: UUID) -> None:
        self._table.delete_item(Key={"pk": f"PROFILE#{user_id}", "sk": "PROFILE"})
        logger.info("dynamodb.profile.deleted", user_id=str(user_id))

    @staticmethod
    def _to_item(p: UserProfile) -> dict:  # type: ignore[type-arg]
        item: dict = {  # type: ignore[type-arg]
            "pk": f"PROFILE#{p.user_id}",
            "sk": "PROFILE",
            "user_id": str(p.user_id),
            "email": p.email,
            "full_name": p.full_name,
            "phone": p.phone,
            "date_of_birth": p.date_of_birth,
            "address": {
                "street": p.address.street,
                "city": p.address.city,
                "state": p.address.state,
                "postal_code": p.address.postal_code,
                "country": p.address.country,
            },
            "email_verified": p.email_verified,
            "require_password_change": p.require_password_change,
            "created_at": p.created_at.isoformat(),
            "updated_at": p.updated_at.isoformat(),
        }
        if p.migrated_from:
            item["migrated_from"] = p.migrated_from
        if p.migrated_at:
            item["migrated_at"] = p.migrated_at.isoformat()
        return item

    @staticmethod
    def _from_item(item: dict) -> UserProfile:  # type: ignore[type-arg]
        addr = item.get("address", {})
        migrated_at = item.get("migrated_at")
        return UserProfile(
            user_id=UUID(item["user_id"]),
            email=item["email"],
            full_name=item["full_name"],
            phone=item.get("phone", ""),
            date_of_birth=item.get("date_of_birth", ""),
            address=Address(
                street=addr.get("street", ""),
                city=addr.get("city", ""),
                state=addr.get("state", ""),
                postal_code=addr.get("postal_code", ""),
                country=addr.get("country", ""),
            ),
            email_verified=item.get("email_verified", False),
            require_password_change=item.get("require_password_change", False),
            created_at=datetime.fromisoformat(item["created_at"]),
            updated_at=datetime.fromisoformat(item["updated_at"]),
            migrated_from=item.get("migrated_from"),
            migrated_at=datetime.fromisoformat(migrated_at) if migrated_at else None,
        )
