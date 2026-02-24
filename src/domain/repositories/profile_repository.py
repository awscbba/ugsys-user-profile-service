"""Outbound port — abstract profile repository."""

from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.entities.profile import UserProfile


class ProfileRepository(ABC):
    @abstractmethod
    async def save(self, profile: UserProfile) -> UserProfile: ...

    @abstractmethod
    async def update(self, profile: UserProfile) -> UserProfile: ...

    @abstractmethod
    async def find_by_user_id(self, user_id: UUID) -> UserProfile | None: ...

    @abstractmethod
    async def delete(self, user_id: UUID) -> None: ...
