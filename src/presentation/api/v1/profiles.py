"""Profiles router — /api/v1/profiles endpoints."""

from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from src.application.commands.profile_commands import (
    UpdateContactCommand,
    UpdatePersonalCommand,
)
from src.application.queries.profile_queries import GetProfileQuery
from src.application.services.profile_service import ProfileService
from src.domain.entities.profile import UserProfile

logger = structlog.get_logger()
router = APIRouter(prefix="/profiles", tags=["profiles"])
bearer = HTTPBearer()


class UpdateContactRequest(BaseModel):
    phone: str | None = None
    street: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str | None = None


class UpdatePersonalRequest(BaseModel):
    full_name: str | None = None
    date_of_birth: str | None = None


def get_profile_service() -> ProfileService:  # pragma: no cover
    raise NotImplementedError("ProfileService not wired")


def get_token_service() -> object:  # pragma: no cover
    raise NotImplementedError("TokenService not wired")


def _extract_claims(
    credentials: HTTPAuthorizationCredentials,
    token_service: object,
) -> dict:  # type: ignore[type-arg]
    try:
        return token_service.verify_token(credentials.credentials)  # type: ignore[attr-defined]
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


def _profile_dict(p: UserProfile) -> dict:  # type: ignore[type-arg]
    return {
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
    }


@router.get("/me")
async def get_my_profile(
    credentials: HTTPAuthorizationCredentials = Security(bearer),  # noqa: B008
    profile_service: ProfileService = Depends(get_profile_service),  # noqa: B008
    token_service: object = Depends(get_token_service),
) -> dict:  # type: ignore[type-arg]
    claims = _extract_claims(credentials, token_service)
    user_id = UUID(str(claims["sub"]))
    try:
        profile = await profile_service.get_profile(
            GetProfileQuery(user_id=user_id, requester_id=str(user_id))
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    return _profile_dict(profile)


@router.get("/{user_id}")
async def get_profile(
    user_id: UUID,
    credentials: HTTPAuthorizationCredentials = Security(bearer),  # noqa: B008
    profile_service: ProfileService = Depends(get_profile_service),  # noqa: B008
    token_service: object = Depends(get_token_service),
) -> dict:  # type: ignore[type-arg]
    claims = _extract_claims(credentials, token_service)
    requester_id = str(claims["sub"])
    roles: list[str] = list(claims.get("roles", []))
    is_admin = "admin" in roles or "super_admin" in roles
    try:
        profile = await profile_service.get_profile(
            GetProfileQuery(user_id=user_id, requester_id=requester_id, is_admin=is_admin)
        )
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    return _profile_dict(profile)


@router.patch("/{user_id}/contact")
async def update_contact(
    user_id: UUID,
    body: UpdateContactRequest,
    credentials: HTTPAuthorizationCredentials = Security(bearer),  # noqa: B008
    profile_service: ProfileService = Depends(get_profile_service),  # noqa: B008
    token_service: object = Depends(get_token_service),
) -> dict:  # type: ignore[type-arg]
    claims = _extract_claims(credentials, token_service)
    requester_id = str(claims["sub"])
    try:
        profile = await profile_service.update_contact(
            UpdateContactCommand(
                user_id=user_id,
                requester_id=requester_id,
                phone=body.phone,
                street=body.street,
                city=body.city,
                state=body.state,
                postal_code=body.postal_code,
                country=body.country,
            )
        )
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    return _profile_dict(profile)


@router.patch("/{user_id}/personal")
async def update_personal(
    user_id: UUID,
    body: UpdatePersonalRequest,
    credentials: HTTPAuthorizationCredentials = Security(bearer),  # noqa: B008
    profile_service: ProfileService = Depends(get_profile_service),  # noqa: B008
    token_service: object = Depends(get_token_service),
) -> dict:  # type: ignore[type-arg]
    claims = _extract_claims(credentials, token_service)
    requester_id = str(claims["sub"])
    try:
        profile = await profile_service.update_personal(
            UpdatePersonalCommand(
                user_id=user_id,
                requester_id=requester_id,
                full_name=body.full_name,
                date_of_birth=body.date_of_birth,
            )
        )
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    return _profile_dict(profile)
