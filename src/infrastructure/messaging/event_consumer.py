"""EventBridge event consumer — Lambda handler for identity-manager events."""

from typing import Any
from uuid import UUID

import structlog

from src.application.commands.profile_commands import CreateProfileCommand
from src.application.services.profile_service import ProfileService
from src.domain.exceptions import ConflictError

logger = structlog.get_logger()


async def _handle_user_registered(event_detail: dict[str, Any], service: ProfileService) -> None:
    """Create a profile when a new user registers. Skip if profile already exists."""
    user_id = event_detail.get("user_id")
    email = event_detail.get("email")
    full_name = event_detail.get("full_name")

    if not user_id or not email or not full_name:
        logger.error(
            "event_consumer.user_registered.missing_fields",
            user_id=user_id,
            has_email=bool(email),
            has_full_name=bool(full_name),
        )
        return

    try:
        cmd = CreateProfileCommand(
            user_id=UUID(str(user_id)),
            email=str(email),
            full_name=str(full_name),
        )
        await service.create_profile(cmd)
        logger.info("event_consumer.user_registered.profile_created", user_id=str(user_id))
    except ConflictError:
        logger.warning("event_consumer.user_registered.already_exists", user_id=str(user_id))
    except Exception as e:
        logger.error("event_consumer.user_registered.failed", user_id=str(user_id), error=str(e))


async def _handle_user_deactivated(event_detail: dict[str, Any], service: ProfileService) -> None:
    """Soft-delete a profile when a user is deactivated. Skip if not found."""
    user_id = event_detail.get("user_id")
    if not user_id:
        logger.error("event_consumer.user_deactivated.missing_user_id")
        return

    try:
        await service.deactivate_profile(UUID(str(user_id)))
        logger.info("event_consumer.user_deactivated.handled", user_id=str(user_id))
    except Exception as e:
        logger.error("event_consumer.user_deactivated.failed", user_id=str(user_id), error=str(e))


async def _handle_password_changed(event_detail: dict[str, Any], service: ProfileService) -> None:
    """Clear the require_password_change flag when a user changes their password."""
    user_id = event_detail.get("user_id")
    if not user_id:
        logger.error("event_consumer.password_changed.missing_user_id")
        return

    try:
        await service.clear_password_change_flag(UUID(str(user_id)))
        logger.info("event_consumer.password_changed.handled", user_id=str(user_id))
    except Exception as e:
        logger.error("event_consumer.password_changed.failed", user_id=str(user_id), error=str(e))


async def handle_event(event: dict[str, Any], service: ProfileService) -> None:
    """Route an EventBridge event to the appropriate handler."""
    detail_type = event.get("detail-type", "")
    detail = event.get("detail", {})

    logger.info("event_consumer.received", detail_type=detail_type)

    match detail_type:
        case "identity.user.registered":
            await _handle_user_registered(detail, service)
        case "identity.user.deactivated":
            await _handle_user_deactivated(detail, service)
        case "identity.auth.password_changed":
            await _handle_password_changed(detail, service)
        case _:
            logger.warning("event_consumer.unknown_event_type", detail_type=detail_type)
