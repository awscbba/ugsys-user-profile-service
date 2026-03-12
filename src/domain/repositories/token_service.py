"""Token service port — outbound interface for JWT verification."""

from abc import ABC, abstractmethod


class TokenService(ABC):
    @abstractmethod
    def verify_token(self, token: str) -> dict[str, object]:
        """Verify a JWT and return its claims. Raises AuthenticationError on failure."""
        ...
