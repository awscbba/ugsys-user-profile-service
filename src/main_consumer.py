"""Lambda entry point for EventBridge event consumer.

Wires all dependencies and invokes handle_event() via asyncio.run().
configure_logging() is called at module level — runs once per cold start.
"""

import asyncio
from typing import Any

import aioboto3
import structlog

from src.config import settings
from src.infrastructure.adapters.s3_avatar_storage import S3AvatarStorage
from src.infrastructure.logging import configure_logging
from src.infrastructure.messaging.event_consumer import handle_event
from src.infrastructure.messaging.event_publisher import EventBridgePublisher
from src.infrastructure.persistence.dynamodb_profile_repository import DynamoDBProfileRepository

configure_logging(settings.service_name, settings.log_level)
logger = structlog.get_logger()


def lambda_handler(event: dict[str, Any], context: object) -> dict[str, Any]:
    """AWS Lambda entry point for EventBridge consumer."""
    detail_type = event.get("detail-type", "")
    logger.info("consumer.invoked", detail_type=detail_type)

    # Extract payload from the EventBridge envelope's detail field
    raw_detail = event.get("detail", {})
    payload = raw_detail.get("payload", raw_detail)
    routed_event = {"detail-type": detail_type, "detail": payload}

    async def _run() -> None:
        session = aioboto3.Session()
        async with (
            session.client("dynamodb", region_name=settings.aws_region) as _,
            session.client("s3", region_name=settings.aws_region) as _,
        ):
            repo = DynamoDBProfileRepository(
                table_name=settings.profiles_table,
                region=settings.aws_region,
                session=session,
            )
            avatar_storage = S3AvatarStorage(
                bucket_name=settings.avatars_bucket_name,
                region=settings.aws_region,
                session=session,
            )
            publisher = EventBridgePublisher(
                event_bus_name=settings.event_bus_name,
                region=settings.aws_region,
                session=session,
            )

            from src.application.services.profile_service import ProfileService

            service = ProfileService(
                profile_repo=repo,
                event_publisher=publisher,
                avatar_storage=avatar_storage,
            )
            await handle_event(routed_event, service)

    try:
        asyncio.run(_run())
    except Exception as e:
        logger.error("consumer.failed", detail_type=detail_type, error=str(e))
        raise

    return {"statusCode": 200, "body": "OK"}
