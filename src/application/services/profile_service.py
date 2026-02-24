"""Profile application service — orchestrates profile use cases."""

from typing import Protocol
from uuid import UUID

import structlog

from src.application.commands.profile_commands import (
    CreateProfileCommand,
    DeleteProfileCommand,
    UpdateContactCommand,
    UpdatePersonalCommand,
)
from src.application.queries.profile_queries import GetProfileQuery
from src.domain.entities.profile import Address, UserProfile
from src.domain.repositories.profile_repository import ProfileRepository

logger = structlog.get_logger()


class EventPublisherProtocol(Protocol):
    def publish(self, source: str, detail_type: str, detail: dict) -> None:  # type: ignore[type-arg]
        ...


class ProfileService:
    def __init__(
        self,
        profile_repo: ProfileRepository,
        event_publisher: EventPublisherProtocol | None = None,
    ) -> None:
        self._repo = profile_repo
        self._events = event_publisher

    async def get_profile(self, query: GetProfileQuery) -> UserProfile:
        logger.info("profile_service.get.started", user_id=str(query.user_id))
        profile = await self._repo.find_by_user_id(query.user_id)
        if not profile:
            raise ValueError(f"Profile not found: {query.user_id}")
        # IDOR — non-admins can only access their own profile
        if not query.is_admin and str(profile.user_id) != query.requester_id:
            logger.warning(
                "profile_service.get.forbidden",
                requester=query.requester_id,
                target=str(query.user_id),
            )
            raise PermissionError("Access denied")
        logger.info("profile_service.get.completed", user_id=str(profile.user_id))
        return profile

    async def create_profile(self, command: CreateProfileCommand) -> UserProfile:
        logger.info("profile_service.create.started", user_id=str(command.user_id))
        existing = await self._repo.find_by_user_id(command.user_id)
        if existing:
            raise ValueError(f"Profile already exists: {command.user_id}")
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
        logger.info("profile_service.create.completed", user_id=str(saved.user_id))
        if self._events:
            self._events.publish(
                source="ugsys.user-profile-service",
                detail_type="profile.created",
                detail={"user_id": str(saved.user_id)},
            )
        return saved

    async def update_contact(self, command: UpdateContactCommand) -> UserProfile:
        logger.info("profile_service.update_contact.started", user_id=str(command.user_id))
        profile = await self._repo.find_by_user_id(command.user_id)
        if not profile:
            raise ValueError(f"Profile not found: {command.user_id}")
        if str(profile.user_id) != command.requester_id:
            raise PermissionError("Access denied")
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
        logger.info("profile_service.update_contact.completed", user_id=str(updated.user_id))
        if self._events:
            self._events.publish(
                source="ugsys.user-profile-service",
                detail_type="profile.updated",
                detail={"user_id": str(updated.user_id)},
            )
        return updated

    async def update_personal(self, command: UpdatePersonalCommand) -> UserProfile:
        logger.info("profile_service.update_personal.started", user_id=str(command.user_id))
        profile = await self._repo.find_by_user_id(command.user_id)
        if not profile:
            raise ValueError(f"Profile not found: {command.user_id}")
        if str(profile.user_id) != command.requester_id:
            raise PermissionError("Access denied")
        profile.update_personal(
            full_name=command.full_name,
            date_of_birth=command.date_of_birth,
        )
        updated = await self._repo.update(profile)
        logger.info("profile_service.update_personal.completed", user_id=str(updated.user_id))
        if self._events:
            self._events.publish(
                source="ugsys.user-profile-service",
                detail_type="profile.updated",
                detail={"user_id": str(updated.user_id)},
            )
        return updated

    async def delete_profile(self, command: DeleteProfileCommand) -> None:
        logger.info("profile_service.delete.started", user_id=str(command.user_id))
        await self._repo.delete(command.user_id)
        logger.info("profile_service.delete.completed", user_id=str(command.user_id))
        if self._events:
            self._events.publish(
                source="ugsys.user-profile-service",
                detail_type="profile.deleted",
                detail={"user_id": str(command.user_id)},
            )

    async def get_profile_by_id(self, user_id: UUID) -> UserProfile | None:
        """Internal use — S2S calls from other services."""
        return await self._repo.find_by_user_id(user_id)
