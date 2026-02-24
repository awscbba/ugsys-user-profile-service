"""Queries for profile read operations."""

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class GetProfileQuery:
    user_id: UUID
    requester_id: str
    is_admin: bool = False
