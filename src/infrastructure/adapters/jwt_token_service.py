"""JWT token service — verify-only adapter for ugsys-user-profile-service.

This service only verifies tokens issued by ugsys-identity-manager.
It never signs tokens — private_key is intentionally unused.
verify_token is synchronous — no blacklist check needed in this service.
"""

from __future__ import annotations

import jwt

from src.domain.exceptions import AuthenticationError
from src.domain.repositories.token_service import TokenService


class JWTTokenService(TokenService):
    def __init__(
        self,
        private_key: str,  # unused — kept for interface compatibility
        public_key: str,
        key_id: str = "ugsys-v1",
        audience: str = "admin-panel",
        retiring_public_key: str | None = None,
        retiring_key_id: str | None = None,
        **_kwargs: object,
    ) -> None:
        self._public_key = public_key
        self._key_id = key_id
        self._audience = audience
        self._retiring_public_key = retiring_public_key
        self._retiring_key_id = retiring_key_id

    def verify_token(self, token: str) -> dict[str, object]:
        # Step 1: Check algorithm BEFORE signature verification (prevents alg confusion)
        try:
            header = jwt.get_unverified_header(token)
        except jwt.PyJWTError as e:
            raise AuthenticationError(
                message=f"Invalid token header: {e}",
                user_message="Invalid or expired token",
                error_code="INVALID_TOKEN",
            ) from e

        if header.get("alg") != "RS256":
            raise AuthenticationError(
                message=f"Rejected token with algorithm '{header.get('alg')}' — only RS256 allowed",
                user_message="Invalid or expired token",
                error_code="INVALID_TOKEN",
            )

        # Step 2: Select public key by kid
        kid = header.get("kid", "")
        if kid == self._key_id:
            verify_key = self._public_key
        elif self._retiring_key_id and kid == self._retiring_key_id:
            if self._retiring_public_key is None:
                raise AuthenticationError(
                    message=f"Retiring key '{kid}' referenced but not configured",
                    user_message="Invalid or expired token",
                    error_code="INVALID_TOKEN",
                )
            verify_key = self._retiring_public_key
        else:
            raise AuthenticationError(
                message=f"Unknown kid '{kid}' — expected '{self._key_id}'",
                user_message="Invalid or expired token",
                error_code="INVALID_TOKEN",
            )

        # Step 3: Decode and verify signature
        # Decode without audience enforcement — aud is only present on access tokens.
        # Internal tokens (refresh, password_reset, service) have no aud claim by design.
        try:
            payload: dict[str, object] = jwt.decode(
                token,
                verify_key,
                algorithms=["RS256"],
                options={"verify_aud": False},
            )
        except jwt.PyJWTError as e:
            raise AuthenticationError(
                message=f"Token verification failed: {e}",
                user_message="Invalid or expired token",
                error_code="INVALID_TOKEN",
            ) from e

        # Step 4: Validate required claims
        for claim in ("sub", "exp", "iat", "iss"):
            if claim not in payload:
                raise AuthenticationError(
                    message=f"Token missing required claim: '{claim}'",
                    user_message="Invalid or expired token",
                    error_code="INVALID_TOKEN",
                )

        # Step 4b: Enforce aud for access tokens only
        token_type = payload.get("type", "")
        if token_type == "access":  # noqa: S105
            token_aud = payload.get("aud")
            if token_aud != self._audience:
                raise AuthenticationError(
                    message=(
                        f"Token audience '{token_aud}' does not match expected '{self._audience}'"
                    ),
                    user_message="Invalid or expired token",
                    error_code="INVALID_TOKEN",
                )

        return payload
