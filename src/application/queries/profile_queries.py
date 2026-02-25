"""Queries for profile read operations."""

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class GetProfileQuery:
    user_id: UUID
    requester_id: str
    is_admin: bool = False


@dataclass(frozen=True)
class ListProfilesQuery:
    requester_id: str
    is_admin: bool
    page: int = 1
    page_size: int = 20
