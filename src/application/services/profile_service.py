"""Profile application service — orchestrates profile use cases."""

import time
from datetime import UTC, datetime
from uuid import UUID

import structlog

from src.application.commands.profile_commands import (
    CreateProfileCommand,
    DeleteAvatarCommand,
    DeleteProfileCommand,
    SoftDeleteProfileCommand,
    UpdateContactCommand,
    UpdateDisplayCommand,
    UpdatePersonalCommand,
    UpdatePreferencesCommand,
    UploadAvatarCommand,
)
from src.application.queries.profile_queries import GetProfileQuery, ListProfilesQuery
from src.domain.entities.profile import Address, UserProfile
from src.domain.exceptions import (
    AuthorizationError,
    ConflictError,
    ExternalServiceError,
    NotFoundError,
    ValidationError,
)
from src.domain.repositories.avatar_storage import AvatarStorage
from src.domain.repositories.event_publisher import EventPublisher
from src.domain.repositories.profile_repository import ProfileRepository
from src.domain.value_objects.notification_preferences import NotificationPreferences

logger = structlog.get_logger()


class ProfileService:
    def __init__(
        self,
        profile_repo: ProfileRepository,
        event_publisher: EventPublisher | None = None,
        avatar_storage: AvatarStorage | None = None,
    ) -> None:
        self._repo = profile_repo
        self._events = event_publisher
        self._avatar_storage = avatar_storage

    async def get_profile(self, query: GetProfileQuery) -> UserProfile:
        start = time.perf_counter()
        logger.info("profile_service.get.started", user_id=str(query.user_id))
        profile = await self._repo.find_by_user_id(query.user_id)
        if not profile:
            raise NotFoundError(
                message=f"Profile not found: {query.user_id}",
                user_message="Profile not found",
            )
        if not query.is_admin and str(profile.user_id) != query.requester_id:
            logger.warning(
                "profile_service.get.forbidden",
                requester=query.requester_id,
                target=str(query.user_id),
            )
            raise AuthorizationError(
                message=f"User {query.requester_id} attempted IDOR on {query.user_id}",
                user_message="Access denied",
            )
        logger.info(
            "profile_service.get.completed",
            user_id=str(profile.user_id),
            duration_ms=round((time.perf_counter() - start) * 1000, 2),
        )
        return profile

    async def create_profile(self, command: CreateProfileCommand) -> UserProfile:
        start = time.perf_counter()
        logger.info("profile_service.create.started", user_id=str(command.user_id))
        existing = await self._repo.find_by_user_id(command.user_id)
        if existing:
            raise ConflictError(
                message=f"Profile already exists: {command.user_id}",
                user_message="A profile already exists for this user",
            )
        profile = UserProfile(
            user_id=command.user_id,
            email=command.email,
            full_name=command.full_name,
            phone=command.phone,
            date_of_birth=command.date_of_birth,
            address=Address(
                street=command.street,
                city=command.city,
                state=command.state,
                postal_code=command.postal_code,
                country=command.country,
            ),
            email_verified=command.email_verified,
            require_password_change=command.require_password_change,
        )
        saved = await self._repo.save(profile)
        logger.info(
            "profile_service.create.completed",
            user_id=str(saved.user_id),
            duration_ms=round((time.perf_counter() - start) * 1000, 2),
        )
        if self._events:
            await self._events.publish(
                detail_type="profile.created",
                payload={"user_id": str(saved.user_id)},
            )
        return saved

    async def update_contact(self, command: UpdateContactCommand) -> UserProfile:
        start = time.perf_counter()
        logger.info("profile_service.update_contact.started", user_id=str(command.user_id))
        profile = await self._repo.find_by_user_id(command.user_id)
        if not profile:
            raise NotFoundError(
                message=f"Profile not found: {command.user_id}",
                user_message="Profile not found",
            )
        if not getattr(command, "is_admin", False) and str(profile.user_id) != command.requester_id:
            raise AuthorizationError(
                message=f"User {command.requester_id} attempted IDOR on {command.user_id}",
                user_message="Access denied",
            )
        address = None
        if any(
            v is not None
            for v in [
                command.street,
                command.city,
                command.state,
                command.postal_code,
                command.country,
            ]
        ):
            address = Address(
                street=command.street or profile.address.street,
                city=command.city or profile.address.city,
                state=command.state or profile.address.state,
                postal_code=command.postal_code or profile.address.postal_code,
                country=command.country or profile.address.country,
            )
        profile.update_contact(phone=command.phone, address=address)
        updated = await self._repo.update(profile)
        logger.info(
            "profile_service.update_contact.completed",
            user_id=str(updated.user_id),
            duration_ms=round((time.perf_counter() - start) * 1000, 2),
        )
        if self._events:
            await self._events.publish(
                detail_type="profile.updated",
                payload={"user_id": str(updated.user_id), "changed_fields": ["contact"]},
            )
        return updated

    async def update_personal(self, command: UpdatePersonalCommand) -> UserProfile:
        start = time.perf_counter()
        logger.info("profile_service.update_personal.started", user_id=str(command.user_id))
        profile = await self._repo.find_by_user_id(command.user_id)
        if not profile:
            raise NotFoundError(
                message=f"Profile not found: {command.user_id}",
                user_message="Profile not found",
            )
        if str(profile.user_id) != command.requester_id:
            raise AuthorizationError(
                message=f"User {command.requester_id} attempted IDOR on {command.user_id}",
                user_message="Access denied",
            )
        profile.update_personal(full_name=command.full_name, date_of_birth=command.date_of_birth)
        updated = await self._repo.update(profile)
        logger.info(
            "profile_service.update_personal.completed",
            user_id=str(updated.user_id),
            duration_ms=round((time.perf_counter() - start) * 1000, 2),
        )
        if self._events:
            await self._events.publish(
                detail_type="profile.updated",
                payload={"user_id": str(updated.user_id), "changed_fields": ["personal"]},
            )
        return updated

    async def delete_profile(self, command: DeleteProfileCommand) -> None:
        start = time.perf_counter()
        logger.info("profile_service.delete.started", user_id=str(command.user_id))
        await self._repo.delete(command.user_id)
        logger.info(
            "profile_service.delete.completed",
            user_id=str(command.user_id),
            duration_ms=round((time.perf_counter() - start) * 1000, 2),
        )
        if self._events:
            await self._events.publish(
                detail_type="profile.deleted",
                payload={"user_id": str(command.user_id)},
            )

    async def upload_avatar(self, command: UploadAvatarCommand) -> UserProfile:
        start = time.perf_counter()
        logger.info("profile_service.upload_avatar.started", user_id=str(command.user_id))
        # Validate content type
        allowed_types = {"image/jpeg", "image/png", "image/webp"}
        if command.content_type not in allowed_types:
            raise ValidationError(
                message=f"Invalid content type: {command.content_type}",
                user_message="Avatar must be JPEG, PNG, or WebP",
            )
        # Validate file size (5 MB max)
        max_size = 5 * 1024 * 1024
        if len(command.file_bytes) > max_size:
            raise ValidationError(
                message=f"Avatar file too large: {len(command.file_bytes)} bytes",
                user_message="Avatar file must be 5 MB or smaller",
            )
        # IDOR check
        profile = await self._repo.find_by_user_id(command.user_id)
        if not profile:
            raise NotFoundError(
                message=f"Profile not found: {command.user_id}",
                user_message="Profile not found",
            )
        if not command.is_admin and str(profile.user_id) != command.requester_id:
            raise AuthorizationError(
                message=f"User {command.requester_id} attempted IDOR on {command.user_id}",
                user_message="Access denied",
            )
        if not self._avatar_storage:
            raise ExternalServiceError(
                message="AvatarStorage not configured",
                user_message="Avatar upload is not available",
            )
        ext_map = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
        extension = ext_map[command.content_type]
        avatar_url = await self._avatar_storage.upload(
            command.user_id, command.file_bytes, extension
        )
        profile.avatar_url = avatar_url
        profile.updated_at = datetime.now(UTC)
        updated = await self._repo.update(profile)
        logger.info(
            "profile_service.upload_avatar.completed",
            user_id=str(updated.user_id),
            duration_ms=round((time.perf_counter() - start) * 1000, 2),
        )
        if self._events:
            await self._events.publish(
                detail_type="profile.avatar_updated",
                payload={"user_id": str(updated.user_id), "avatar_url": avatar_url},
            )
        return updated

    async def delete_avatar(self, command: DeleteAvatarCommand) -> UserProfile:
        start = time.perf_counter()
        logger.info("profile_service.delete_avatar.started", user_id=str(command.user_id))
        profile = await self._repo.find_by_user_id(command.user_id)
        if not profile:
            raise NotFoundError(
                message=f"Profile not found: {command.user_id}",
                user_message="Profile not found",
            )
        if not command.is_admin and str(profile.user_id) != command.requester_id:
            raise AuthorizationError(
                message=f"User {command.requester_id} attempted IDOR on {command.user_id}",
                user_message="Access denied",
            )
        # Delete from storage if avatar exists and storage is configured
        if profile.avatar_url and self._avatar_storage:
            ext = profile.avatar_url.rsplit(".", 1)[-1] if "." in profile.avatar_url else "jpg"
            await self._avatar_storage.delete(command.user_id, ext)
        profile.avatar_url = None
        profile.updated_at = datetime.now(UTC)
        updated = await self._repo.update(profile)
        logger.info(
            "profile_service.delete_avatar.completed",
            user_id=str(updated.user_id),
            duration_ms=round((time.perf_counter() - start) * 1000, 2),
        )
        return updated

    async def update_preferences(self, command: UpdatePreferencesCommand) -> UserProfile:
        start = time.perf_counter()
        logger.info("profile_service.update_preferences.started", user_id=str(command.user_id))
        profile = await self._repo.find_by_user_id(command.user_id)
        if not profile:
            raise NotFoundError(
                message=f"Profile not found: {command.user_id}",
                user_message="Profile not found",
            )
        if not command.is_admin and str(profile.user_id) != command.requester_id:
            raise AuthorizationError(
                message=f"User {command.requester_id} attempted IDOR on {command.user_id}",
                user_message="Access denied",
            )
        # Build updated notification_preferences if any field provided
        notification_preferences = None
        if any(
            v is not None
            for v in [
                command.notification_preferences_email,
                command.notification_preferences_sms,
                command.notification_preferences_whatsapp,
            ]
        ):
            current = profile.notification_preferences
            notification_preferences = NotificationPreferences(
                email=command.notification_preferences_email
                if command.notification_preferences_email is not None
                else current.email,
                sms=command.notification_preferences_sms
                if command.notification_preferences_sms is not None
                else current.sms,
                whatsapp=command.notification_preferences_whatsapp
                if command.notification_preferences_whatsapp is not None
                else current.whatsapp,
            )
        changed_fields = []
        if notification_preferences is not None:
            changed_fields.append("notification_preferences")
        if command.language is not None:
            changed_fields.append("language")
        if command.timezone is not None:
            changed_fields.append("timezone")
        profile.update_preferences(
            notification_preferences=notification_preferences,
            language=command.language,
            timezone=command.timezone,
        )
        updated = await self._repo.update(profile)
        logger.info(
            "profile_service.update_preferences.completed",
            user_id=str(updated.user_id),
            duration_ms=round((time.perf_counter() - start) * 1000, 2),
        )
        if self._events:
            await self._events.publish(
                detail_type="profile.updated",
                payload={"user_id": str(updated.user_id), "changed_fields": changed_fields},
            )
        return updated

    async def update_display(self, command: UpdateDisplayCommand) -> UserProfile:
        start = time.perf_counter()
        logger.info("profile_service.update_display.started", user_id=str(command.user_id))
        # Validate bio length at API level before touching the entity
        if command.bio is not None and len(command.bio) > 500:
            raise ValidationError(
                message=f"Bio too long: {len(command.bio)} chars",
                user_message="Bio must be 500 characters or fewer",
            )
        profile = await self._repo.find_by_user_id(command.user_id)
        if not profile:
            raise NotFoundError(
                message=f"Profile not found: {command.user_id}",
                user_message="Profile not found",
            )
        if not command.is_admin and str(profile.user_id) != command.requester_id:
            raise AuthorizationError(
                message=f"User {command.requester_id} attempted IDOR on {command.user_id}",
                user_message="Access denied",
            )
        changed_fields = []
        if command.bio is not None:
            changed_fields.append("bio")
        if command.display_name is not None:
            changed_fields.append("display_name")
        profile.update_display(bio=command.bio, display_name=command.display_name)
        updated = await self._repo.update(profile)
        logger.info(
            "profile_service.update_display.completed",
            user_id=str(updated.user_id),
            duration_ms=round((time.perf_counter() - start) * 1000, 2),
        )
        if self._events:
            await self._events.publish(
                detail_type="profile.updated",
                payload={"user_id": str(updated.user_id), "changed_fields": changed_fields},
            )
        return updated

    async def list_profiles(self, query: ListProfilesQuery) -> tuple[list[UserProfile], int]:
        start = time.perf_counter()
        logger.info("profile_service.list_profiles.started", requester=query.requester_id)
        if not query.is_admin:
            raise AuthorizationError(
                message=f"Non-admin {query.requester_id} attempted to list profiles",
                user_message="Access denied",
            )
        # Cap page_size at 100
        page_size = min(query.page_size, 100)
        profiles, total = await self._repo.list_profiles(page=query.page, page_size=page_size)
        logger.info(
            "profile_service.list_profiles.completed",
            total=total,
            page=query.page,
            page_size=page_size,
            duration_ms=round((time.perf_counter() - start) * 1000, 2),
        )
        return profiles, total

    async def soft_delete_profile(self, command: SoftDeleteProfileCommand) -> None:
        start = time.perf_counter()
        logger.info("profile_service.soft_delete.started", user_id=str(command.user_id))
        # Only admins can soft-delete (requester_id is verified as admin by the router)
        profile = await self._repo.find_by_user_id(command.user_id)
        if not profile:
            raise NotFoundError(
                message=f"Profile not found: {command.user_id}",
                user_message="Profile not found",
            )
        profile.soft_delete()
        await self._repo.update(profile)
        logger.info(
            "profile_service.soft_delete.completed",
            user_id=str(command.user_id),
            duration_ms=round((time.perf_counter() - start) * 1000, 2),
        )
        if self._events:
            await self._events.publish(
                detail_type="profile.deleted",
                payload={"user_id": str(command.user_id)},
            )

    async def get_profile_by_id(self, user_id: UUID) -> UserProfile | None:
        """Internal use — S2S calls from other services."""
        return await self._repo.find_by_user_id(user_id)
