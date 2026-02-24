"""EventBridge publisher adapter."""

import json

import boto3
import structlog

logger = structlog.get_logger()


class EventBridgePublisher:
    def __init__(self, event_bus_name: str, region: str = "us-east-1") -> None:
        self._bus = event_bus_name
        self._client = boto3.client("events", region_name=region)

    def publish(self, source: str, detail_type: str, detail: dict) -> None:  # type: ignore[type-arg]
        self._client.put_events(
            Entries=[
                {
                    "Source": source,
                    "DetailType": detail_type,
                    "Detail": json.dumps(detail),
                    "EventBusName": self._bus,
                }
            ]
        )
        logger.info("event.published", detail_type=detail_type, source=source)
