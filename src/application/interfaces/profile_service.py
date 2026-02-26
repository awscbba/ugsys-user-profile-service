"""IProfileService — inbound port interface for the profile application service."""

from abc import ABC, abstractmethod
from uuid import UUID

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
from src.domain.entities.profile import UserProfile


class IProfileService(ABC):
    """Inbound port — defines the contract for all profile use cases."""

    @abstractmethod
    async def get_profile(self, query: GetProfileQuery) -> UserProfile: ...

    @abstractmethod
    async def create_profile(self, command: CreateProfileCommand) -> UserProfile: ...

    @abstractmethod
    async def update_contact(self, command: UpdateContactCommand) -> UserProfile: ...

    @abstractmethod
    async def update_personal(self, command: UpdatePersonalCommand) -> UserProfile: ...

    @abstractmethod
    async def delete_profile(self, command: DeleteProfileCommand) -> None: ...

    @abstractmethod
    async def upload_avatar(self, command: UploadAvatarCommand) -> UserProfile: ...

    @abstractmethod
    async def delete_avatar(self, command: DeleteAvatarCommand) -> UserProfile: ...

    @abstractmethod
    async def update_preferences(self, command: UpdatePreferencesCommand) -> UserProfile: ...

    @abstractmethod
    async def update_display(self, command: UpdateDisplayCommand) -> UserProfile: ...

    @abstractmethod
    async def list_profiles(self, query: ListProfilesQuery) -> tuple[list[UserProfile], int]: ...

    @abstractmethod
    async def soft_delete_profile(self, command: SoftDeleteProfileCommand) -> None: ...

    @abstractmethod
    async def get_profile_by_id(self, user_id: UUID) -> UserProfile | None: ...

    @abstractmethod
    async def deactivate_profile(self, user_id: UUID) -> None: ...

    @abstractmethod
    async def clear_password_change_flag(self, user_id: UUID) -> None: ...
