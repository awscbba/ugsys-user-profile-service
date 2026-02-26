"""Unit tests for main.py wiring — TDD Task 8.1.

Verifies EventBridgePublisher is instantiated with a session kwarg of type aioboto3.Session.
"""

import aioboto3

from src.infrastructure.messaging.event_publisher import EventBridgePublisher


def test_event_bridge_publisher_receives_aioboto3_session() -> None:
    """EventBridgePublisher must accept and store a session kwarg of type aioboto3.Session."""
    session = aioboto3.Session()
    publisher = EventBridgePublisher(
        event_bus_name="test-bus",
        region="us-east-1",
        session=session,
    )
    assert isinstance(publisher._session, aioboto3.Session)
    assert publisher._session is session
