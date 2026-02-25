"""EventBridge publisher adapter."""

import json
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import boto3
import structlog

from src.domain.repositories.event_publisher import EventPublisher
from src.presentation.middleware.correlation_id import correlation_id_var

logger = structlog.get_logger()

_SOURCE = "ugsys.user-profile-service"


class EventBridgePublisher(EventPublisher):
    def __init__(self, event_bus_name: str, region: str = "us-east-1") -> None:
        self._bus = event_bus_name
        self._client = boto3.client("events", region_name=region)

    async def publish(self, detail_type: str, payload: dict[str, Any]) -> None:
        event_id = str(uuid4())
        envelope = {
            "event_id": event_id,
            "event_version": "1.0",
            "timestamp": datetime.now(UTC).isoformat(),
            "correlation_id": correlation_id_var.get(""),
            "payload": payload,
        }
        self._client.put_events(
            Entries=[
                {
                    "Source": _SOURCE,
                    "DetailType": detail_type,
                    "Detail": json.dumps(envelope),
                    "EventBusName": self._bus,
                }
            ]
        )
        logger.info("event.published", detail_type=detail_type, event_id=event_id, source=_SOURCE)
