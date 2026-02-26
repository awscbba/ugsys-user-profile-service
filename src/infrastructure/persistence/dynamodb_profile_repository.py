"""DynamoDB adapter implementing ProfileRepository port — aioboto3 async I/O."""

from datetime import datetime
from typing import Any, NoReturn
from uuid import UUID

import aioboto3
import structlog
from botocore.exceptions import ClientError

from src.domain.entities.profile import Address, UserProfile
from src.domain.exceptions import NotFoundError, RepositoryError
from src.domain.repositories.profile_repository import ProfileRepository
from src.domain.value_objects.notification_preferences import NotificationPreferences

logger = structlog.get_logger()


class DynamoDBProfileRepository(ProfileRepository):
    def __init__(
        self,
        table_name: str,
        region: str = "us-east-1",
        session: aioboto3.Session | None = None,
    ) -> None:
        self._table_name = table_name
        self._region = region
        self._session = session or aioboto3.Session()

    # ── Public interface ──────────────────────────────────────────────────────

    async def save(self, profile: UserProfile) -> UserProfile:
        try:
            async with self._session.client("dynamodb", region_name=self._region) as client:
                await client.put_item(
                    TableName=self._table_name,
                    Item=self._to_dynamo_item(profile),
                    ConditionExpression="attribute_not_exists(pk)",
                )
            logger.info("dynamodb.profile.saved", user_id=str(profile.user_id))
            return profile
        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                raise RepositoryError(
                    message=f"Profile {profile.user_id} already exists: {e}",
                    user_message="An unexpected error occurred",
                    error_code="REPOSITORY_ERROR",
                ) from e
            self._raise_repository_error("save", e)

    async def update(self, profile: UserProfile) -> UserProfile:
        try:
            async with self._session.client("dynamodb", region_name=self._region) as client:
                await client.put_item(
                    TableName=self._table_name,
                    Item=self._to_dynamo_item(profile),
                    ConditionExpression="attribute_exists(pk)",
                )
            logger.info("dynamodb.profile.updated", user_id=str(profile.user_id))
            return profile
        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                raise NotFoundError(
                    message=f"Profile {profile.user_id} not found for update: {e}",
                    user_message="Profile not found",
                    error_code="NOT_FOUND",
                ) from e
            self._raise_repository_error("update", e)

    async def find_by_user_id(self, user_id: UUID) -> UserProfile | None:
        try:
            async with self._session.client("dynamodb", region_name=self._region) as client:
                response = await client.get_item(
                    TableName=self._table_name,
                    Key={
                        "pk": {"S": f"PROFILE#{user_id}"},
                        "sk": {"S": "PROFILE"},
                    },
                )
            item = response.get("Item")
            return self._from_dynamo_item(item) if item else None
        except ClientError as e:
            self._raise_repository_error("find_by_user_id", e)

    async def delete(self, user_id: UUID) -> None:
        try:
            async with self._session.client("dynamodb", region_name=self._region) as client:
                await client.delete_item(
                    TableName=self._table_name,
                    Key={
                        "pk": {"S": f"PROFILE#{user_id}"},
                        "sk": {"S": "PROFILE"},
                    },
                )
            logger.info("dynamodb.profile.deleted", user_id=str(user_id))
        except ClientError as e:
            self._raise_repository_error("delete", e)

    async def list_profiles(self, page: int, page_size: int) -> tuple[list[UserProfile], int]:
        """Scan all non-deleted profiles, paginate in-memory."""
        try:
            all_items: list[dict[str, Any]] = []
            scan_kwargs: dict[str, Any] = {
                "TableName": self._table_name,
                "FilterExpression": "attribute_not_exists(deleted_at) OR deleted_at = :null",
                "ExpressionAttributeValues": {":null": {"NULL": True}},
            }
            async with self._session.client("dynamodb", region_name=self._region) as client:
                while True:
                    resp = await client.scan(**scan_kwargs)
                    all_items.extend(resp.get("Items", []))
                    last_key = resp.get("LastEvaluatedKey")
                    if not last_key:
                        break
                    scan_kwargs["ExclusiveStartKey"] = last_key

            total = len(all_items)
            start = (page - 1) * page_size
            page_items = [
                self._from_dynamo_item(item) for item in all_items[start : start + page_size]
            ]
            logger.info("dynamodb.profile.list", total=total, page=page, page_size=page_size)
            return page_items, total
        except ClientError as e:
            self._raise_repository_error("list_profiles", e)

    # ── Serialization ─────────────────────────────────────────────────────────

    @staticmethod
    def _to_item(p: UserProfile) -> dict[str, Any]:
        """Convert domain entity to plain dict (for round-trip tests)."""
        item: dict[str, Any] = {
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
            "notification_preferences": {
                "email": p.notification_preferences.email,
                "sms": p.notification_preferences.sms,
                "whatsapp": p.notification_preferences.whatsapp,
            },
            "language": p.language,
            "timezone": p.timezone,
        }
        if p.avatar_url is not None:
            item["avatar_url"] = p.avatar_url
        if p.bio is not None:
            item["bio"] = p.bio
        if p.display_name is not None:
            item["display_name"] = p.display_name
        if p.deleted_at is not None:
            item["deleted_at"] = p.deleted_at.isoformat()
        if p.migrated_from:
            item["migrated_from"] = p.migrated_from
        if p.migrated_at:
            item["migrated_at"] = p.migrated_at.isoformat()
        return item

    @staticmethod
    def _from_item(item: dict[str, Any]) -> UserProfile:
        """Convert plain dict to domain entity (for round-trip tests)."""
        addr = item.get("address", {})
        np_raw = item.get("notification_preferences", {})
        deleted_at = item.get("deleted_at")
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
            notification_preferences=NotificationPreferences(
                email=np_raw.get("email", True),
                sms=np_raw.get("sms", False),
                whatsapp=np_raw.get("whatsapp", False),
            ),
            language=item.get("language", "es"),
            timezone=item.get("timezone", "America/La_Paz"),
            avatar_url=item.get("avatar_url"),
            bio=item.get("bio"),
            display_name=item.get("display_name"),
            deleted_at=datetime.fromisoformat(deleted_at) if deleted_at else None,
            migrated_from=item.get("migrated_from"),
            migrated_at=datetime.fromisoformat(migrated_at) if migrated_at else None,
        )

    @staticmethod
    def _to_dynamo_item(p: UserProfile) -> dict[str, Any]:
        """Convert domain entity to DynamoDB AttributeValue dict."""
        item: dict[str, Any] = {
            "pk": {"S": f"PROFILE#{p.user_id}"},
            "sk": {"S": "PROFILE"},
            "user_id": {"S": str(p.user_id)},
            "email": {"S": p.email},
            "full_name": {"S": p.full_name},
            "phone": {"S": p.phone},
            "date_of_birth": {"S": p.date_of_birth},
            "address": {
                "M": {
                    "street": {"S": p.address.street},
                    "city": {"S": p.address.city},
                    "state": {"S": p.address.state},
                    "postal_code": {"S": p.address.postal_code},
                    "country": {"S": p.address.country},
                }
            },
            "email_verified": {"BOOL": p.email_verified},
            "require_password_change": {"BOOL": p.require_password_change},
            "created_at": {"S": p.created_at.isoformat()},
            "updated_at": {"S": p.updated_at.isoformat()},
            "notification_preferences": {
                "M": {
                    "email": {"BOOL": p.notification_preferences.email},
                    "sms": {"BOOL": p.notification_preferences.sms},
                    "whatsapp": {"BOOL": p.notification_preferences.whatsapp},
                }
            },
            "language": {"S": p.language},
            "timezone": {"S": p.timezone},
        }
        if p.avatar_url is not None:
            item["avatar_url"] = {"S": p.avatar_url}
        if p.bio is not None:
            item["bio"] = {"S": p.bio}
        if p.display_name is not None:
            item["display_name"] = {"S": p.display_name}
        if p.deleted_at is not None:
            item["deleted_at"] = {"S": p.deleted_at.isoformat()}
        if p.migrated_from:
            item["migrated_from"] = {"S": p.migrated_from}
        if p.migrated_at:
            item["migrated_at"] = {"S": p.migrated_at.isoformat()}
        return item

    @staticmethod
    def _from_dynamo_item(item: dict[str, Any]) -> UserProfile:
        """Convert DynamoDB AttributeValue dict to domain entity."""
        addr = item.get("address", {}).get("M", {})
        np_raw = item.get("notification_preferences", {}).get("M", {})
        deleted_at = item.get("deleted_at", {}).get("S")
        migrated_at = item.get("migrated_at", {}).get("S")
        return UserProfile(
            user_id=UUID(item["user_id"]["S"]),
            email=item["email"]["S"],
            full_name=item["full_name"]["S"],
            phone=item.get("phone", {}).get("S", ""),
            date_of_birth=item.get("date_of_birth", {}).get("S", ""),
            address=Address(
                street=addr.get("street", {}).get("S", ""),
                city=addr.get("city", {}).get("S", ""),
                state=addr.get("state", {}).get("S", ""),
                postal_code=addr.get("postal_code", {}).get("S", ""),
                country=addr.get("country", {}).get("S", ""),
            ),
            email_verified=item.get("email_verified", {}).get("BOOL", False),
            require_password_change=item.get("require_password_change", {}).get("BOOL", False),
            created_at=datetime.fromisoformat(item["created_at"]["S"]),
            updated_at=datetime.fromisoformat(item["updated_at"]["S"]),
            notification_preferences=NotificationPreferences(
                email=np_raw.get("email", {}).get("BOOL", True),
                sms=np_raw.get("sms", {}).get("BOOL", False),
                whatsapp=np_raw.get("whatsapp", {}).get("BOOL", False),
            ),
            language=item.get("language", {}).get("S", "es"),
            timezone=item.get("timezone", {}).get("S", "America/La_Paz"),
            avatar_url=item.get("avatar_url", {}).get("S"),
            bio=item.get("bio", {}).get("S"),
            display_name=item.get("display_name", {}).get("S"),
            deleted_at=datetime.fromisoformat(deleted_at) if deleted_at else None,
            migrated_from=item.get("migrated_from", {}).get("S"),
            migrated_at=datetime.fromisoformat(migrated_at) if migrated_at else None,
        )

    # ── Error handling ────────────────────────────────────────────────────────

    def _raise_repository_error(self, operation: str, e: ClientError) -> NoReturn:
        """Log full ClientError internally, raise safe RepositoryError to callers."""
        logger.error(
            "dynamodb.error",
            operation=operation,
            table=self._table_name,
            error_code=e.response["Error"]["Code"],
            error=str(e),
        )
        raise RepositoryError(
            message=f"DynamoDB {operation} failed on {self._table_name}: {e}",
            user_message="An unexpected error occurred",
            error_code="REPOSITORY_ERROR",
        )
