from abc import ABC, abstractmethod
from uuid import UUID


class AvatarStorage(ABC):
    @abstractmethod
    async def upload(self, user_id: UUID, file_bytes: bytes, extension: str) -> str:
        """Upload avatar bytes and return the public URL."""
        ...

    @abstractmethod
    async def delete(self, user_id: UUID, extension: str) -> None:
        """Delete the avatar for the given user."""
        ...
