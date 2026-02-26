"""Profiles router — /api/v1/profiles endpoints."""

from typing import Any
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, Response, Security, UploadFile, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.application.commands.profile_commands import (
    DeleteAvatarCommand,
    SoftDeleteProfileCommand,
    UpdateContactCommand,
    UpdateDisplayCommand,
    UpdatePersonalCommand,
    UpdatePreferencesCommand,
    UploadAvatarCommand,
)
from src.application.dtos.profile_dtos import (
    ProfileResponse,
    UpdateContactRequest,
    UpdateDisplayRequest,
    UpdatePersonalRequest,
    UpdatePreferencesRequest,
)
from src.application.interfaces.profile_service import IProfileService
from src.application.queries.profile_queries import GetProfileQuery, ListProfilesQuery
from src.domain.exceptions import AuthorizationError
from src.presentation.middleware.correlation_id import correlation_id_var
from src.presentation.response_envelope import list_response, success_response

logger = structlog.get_logger()
router = APIRouter(prefix="/profiles", tags=["profiles"])
bearer = HTTPBearer()


# ── Dependency stubs ───────────────────────────────────────────────────────────


def get_profile_service() -> IProfileService:  # pragma: no cover
    raise NotImplementedError("ProfileService not wired")


def get_token_service() -> object:  # pragma: no cover
    raise NotImplementedError("TokenService not wired")


# ── Helpers ────────────────────────────────────────────────────────────────────


def _extract_claims(
    credentials: HTTPAuthorizationCredentials,
    token_service: object,
) -> dict[str, Any]:
    try:
        result: dict[str, Any] = token_service.verify_token(credentials.credentials)  # type: ignore[attr-defined]
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


# ── Endpoints ──────────────────────────────────────────────────────────────────


@router.get("/me")
async def get_my_profile(
    credentials: HTTPAuthorizationCredentials = Security(bearer),  # noqa: B008
    profile_service: IProfileService = Depends(get_profile_service),  # noqa: B008
    token_service: object = Depends(get_token_service),
) -> dict[str, Any]:
    claims = _extract_claims(credentials, token_service)
    user_id = UUID(str(claims["sub"]))
    request_id = correlation_id_var.get("")
    profile = await profile_service.get_profile(
        GetProfileQuery(user_id=user_id, requester_id=str(user_id))
    )
    data = ProfileResponse.from_domain(profile).model_dump()
    return success_response(data=data, request_id=request_id)


@router.get("/")
async def list_profiles(
    page: int = 1,
    page_size: int = 20,
    credentials: HTTPAuthorizationCredentials = Security(bearer),  # noqa: B008
    profile_service: IProfileService = Depends(get_profile_service),  # noqa: B008
    token_service: object = Depends(get_token_service),
) -> dict[str, Any]:
    """List all profiles — admin only."""
    claims = _extract_claims(credentials, token_service)
    requester_id = str(claims["sub"])
    roles: list[str] = list(claims.get("roles", []))
    is_admin = "admin" in roles or "super_admin" in roles
    request_id = correlation_id_var.get("")

    if not is_admin:
        raise AuthorizationError(
            message=f"User {requester_id} attempted to list profiles without admin role",
            user_message="Access denied",
        )

    profiles, total = await profile_service.list_profiles(
        ListProfilesQuery(
            requester_id=requester_id,
            is_admin=is_admin,
            page=page,
            page_size=page_size,
        )
    )
    return list_response(
        data=[ProfileResponse.from_domain(p).model_dump() for p in profiles],
        total=total,
        page=page,
        page_size=page_size,
        request_id=request_id,
    )


@router.get("/{user_id}")
async def get_profile(
    user_id: UUID,
    credentials: HTTPAuthorizationCredentials = Security(bearer),  # noqa: B008
    profile_service: IProfileService = Depends(get_profile_service),  # noqa: B008
    token_service: object = Depends(get_token_service),
) -> dict[str, Any]:
    claims = _extract_claims(credentials, token_service)
    requester_id = str(claims["sub"])
    roles: list[str] = list(claims.get("roles", []))
    is_admin = "admin" in roles or "super_admin" in roles
    request_id = correlation_id_var.get("")
    profile = await profile_service.get_profile(
        GetProfileQuery(user_id=user_id, requester_id=requester_id, is_admin=is_admin)
    )
    data = ProfileResponse.from_domain(profile).model_dump()
    return success_response(data=data, request_id=request_id)


@router.patch("/{user_id}/contact")
async def update_contact(
    user_id: UUID,
    body: UpdateContactRequest,
    credentials: HTTPAuthorizationCredentials = Security(bearer),  # noqa: B008
    profile_service: IProfileService = Depends(get_profile_service),  # noqa: B008
    token_service: object = Depends(get_token_service),
) -> dict[str, Any]:
    claims = _extract_claims(credentials, token_service)
    requester_id = str(claims["sub"])
    roles: list[str] = list(claims.get("roles", []))
    is_admin = "admin" in roles or "super_admin" in roles
    request_id = correlation_id_var.get("")
    profile = await profile_service.update_contact(
        UpdateContactCommand(
            user_id=user_id,
            requester_id=requester_id,
            is_admin=is_admin,
            phone=body.phone,
            street=body.street,
            city=body.city,
            state=body.state,
            postal_code=body.postal_code,
            country=body.country,
        )
    )
    data = ProfileResponse.from_domain(profile).model_dump()
    return success_response(data=data, request_id=request_id)


@router.patch("/{user_id}/personal")
async def update_personal(
    user_id: UUID,
    body: UpdatePersonalRequest,
    credentials: HTTPAuthorizationCredentials = Security(bearer),  # noqa: B008
    profile_service: IProfileService = Depends(get_profile_service),  # noqa: B008
    token_service: object = Depends(get_token_service),
) -> dict[str, Any]:
    claims = _extract_claims(credentials, token_service)
    requester_id = str(claims["sub"])
    request_id = correlation_id_var.get("")
    profile = await profile_service.update_personal(
        UpdatePersonalCommand(
            user_id=user_id,
            requester_id=requester_id,
            full_name=body.full_name,
            date_of_birth=body.date_of_birth,
        )
    )
    data = ProfileResponse.from_domain(profile).model_dump()
    return success_response(data=data, request_id=request_id)


@router.post("/{user_id}/avatar")
async def upload_avatar(
    user_id: UUID,
    file: UploadFile = File(...),  # noqa: B008
    credentials: HTTPAuthorizationCredentials = Security(bearer),  # noqa: B008
    profile_service: IProfileService = Depends(get_profile_service),  # noqa: B008
    token_service: object = Depends(get_token_service),
) -> dict[str, Any]:
    claims = _extract_claims(credentials, token_service)
    requester_id = str(claims["sub"])
    roles: list[str] = list(claims.get("roles", []))
    is_admin = "admin" in roles or "super_admin" in roles
    request_id = correlation_id_var.get("")
    file_bytes = await file.read()
    profile = await profile_service.upload_avatar(
        UploadAvatarCommand(
            user_id=user_id,
            requester_id=requester_id,
            is_admin=is_admin,
            file_bytes=file_bytes,
            content_type=file.content_type or "",
        )
    )
    data = ProfileResponse.from_domain(profile).model_dump()
    return success_response(data=data, request_id=request_id)


@router.delete("/{user_id}/avatar", status_code=status.HTTP_204_NO_CONTENT)
async def delete_avatar(
    user_id: UUID,
    credentials: HTTPAuthorizationCredentials = Security(bearer),  # noqa: B008
    profile_service: IProfileService = Depends(get_profile_service),  # noqa: B008
    token_service: object = Depends(get_token_service),
) -> Response:
    claims = _extract_claims(credentials, token_service)
    requester_id = str(claims["sub"])
    roles: list[str] = list(claims.get("roles", []))
    is_admin = "admin" in roles or "super_admin" in roles
    await profile_service.delete_avatar(
        DeleteAvatarCommand(
            user_id=user_id,
            requester_id=requester_id,
            is_admin=is_admin,
        )
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/{user_id}/preferences")
async def update_preferences(
    user_id: UUID,
    body: UpdatePreferencesRequest,
    credentials: HTTPAuthorizationCredentials = Security(bearer),  # noqa: B008
    profile_service: IProfileService = Depends(get_profile_service),  # noqa: B008
    token_service: object = Depends(get_token_service),
) -> dict[str, Any]:
    claims = _extract_claims(credentials, token_service)
    requester_id = str(claims["sub"])
    roles: list[str] = list(claims.get("roles", []))
    is_admin = "admin" in roles or "super_admin" in roles
    request_id = correlation_id_var.get("")
    profile = await profile_service.update_preferences(
        UpdatePreferencesCommand(
            user_id=user_id,
            requester_id=requester_id,
            is_admin=is_admin,
            notification_preferences_email=body.notification_preferences_email,
            notification_preferences_sms=body.notification_preferences_sms,
            notification_preferences_whatsapp=body.notification_preferences_whatsapp,
            language=body.language,
            timezone=body.timezone,
        )
    )
    data = ProfileResponse.from_domain(profile).model_dump()
    return success_response(data=data, request_id=request_id)


@router.patch("/{user_id}/display")
async def update_display(
    user_id: UUID,
    body: UpdateDisplayRequest,
    credentials: HTTPAuthorizationCredentials = Security(bearer),  # noqa: B008
    profile_service: IProfileService = Depends(get_profile_service),  # noqa: B008
    token_service: object = Depends(get_token_service),
) -> dict[str, Any]:
    claims = _extract_claims(credentials, token_service)
    requester_id = str(claims["sub"])
    roles: list[str] = list(claims.get("roles", []))
    is_admin = "admin" in roles or "super_admin" in roles
    request_id = correlation_id_var.get("")
    profile = await profile_service.update_display(
        UpdateDisplayCommand(
            user_id=user_id,
            requester_id=requester_id,
            is_admin=is_admin,
            bio=body.bio,
            display_name=body.display_name,
        )
    )
    data = ProfileResponse.from_domain(profile).model_dump()
    return success_response(data=data, request_id=request_id)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def soft_delete_profile(
    user_id: UUID,
    credentials: HTTPAuthorizationCredentials = Security(bearer),  # noqa: B008
    profile_service: IProfileService = Depends(get_profile_service),  # noqa: B008
    token_service: object = Depends(get_token_service),
) -> Response:
    """Soft-delete a profile — admin only."""
    claims = _extract_claims(credentials, token_service)
    requester_id = str(claims["sub"])
    roles: list[str] = list(claims.get("roles", []))
    is_admin = "admin" in roles or "super_admin" in roles

    if not is_admin:
        raise AuthorizationError(
            message=f"User {requester_id} attempted to delete profile {user_id} without admin role",
            user_message="Access denied",
        )

    await profile_service.soft_delete_profile(
        SoftDeleteProfileCommand(user_id=user_id, requester_id=requester_id)
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
