from abc import ABC, abstractmethod
from typing import Any


class EventPublisher(ABC):
    @abstractmethod
    async def publish(self, detail_type: str, payload: dict[str, Any]) -> None: ...
