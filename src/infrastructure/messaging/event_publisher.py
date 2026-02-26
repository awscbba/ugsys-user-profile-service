"""EventBridge publisher adapter — async aioboto3 implementation."""

import json
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import aioboto3
import structlog
from botocore.exceptions import ClientError

from src.domain.exceptions import ExternalServiceError
from src.domain.repositories.event_publisher import EventPublisher
from src.presentation.middleware.correlation_id import correlation_id_var

logger = structlog.get_logger()

_SOURCE = "ugsys.user-profile-service"


class EventBridgePublisher(EventPublisher):
    def __init__(
        self,
        event_bus_name: str,
        region: str = "us-east-1",
        session: aioboto3.Session | None = None,
    ) -> None:
        self._bus = event_bus_name
        self._region = region
        self._session = session or aioboto3.Session()

    async def publish(self, detail_type: str, payload: dict[str, Any]) -> None:
        event_id = str(uuid4())
        envelope = {
            "event_id": event_id,
            "event_version": "1.0",
            "timestamp": datetime.now(UTC).isoformat(),
            "correlation_id": correlation_id_var.get(""),
            "payload": payload,
        }
        try:
            async with self._session.client("events", region_name=self._region) as client:
                response = await client.put_events(
                    Entries=[
                        {
                            "Source": _SOURCE,
                            "DetailType": detail_type,
                            "Detail": json.dumps(envelope),
                            "EventBusName": self._bus,
                        }
                    ]
                )
            if response["FailedEntryCount"] > 0:
                failed = response.get("Entries", [])
                raise ExternalServiceError(
                    message=f"EventBridge put_events partial failure: {failed}",
                    user_message="An unexpected error occurred",
                    error_code="EXTERNAL_SERVICE_ERROR",
                )
        except ExternalServiceError:
            raise
        except (ClientError, Exception) as e:
            logger.error(
                "event.publish_failed",
                detail_type=detail_type,
                error=str(e),
            )
            raise ExternalServiceError(
                message=f"EventBridge publish failed for {detail_type}: {e}",
                user_message="An unexpected error occurred",
                error_code="EXTERNAL_SERVICE_ERROR",
            ) from e

        logger.info("event.published", detail_type=detail_type, event_id=event_id, source=_SOURCE)
