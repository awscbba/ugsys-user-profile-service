"""Service configuration — loaded from environment variables."""

import os

from pydantic_settings import BaseSettings, SettingsConfigDict


def _resolve_environment() -> str:
    """Accept APP_ENV (CDK convention) or ENVIRONMENT — APP_ENV takes precedence."""
    return os.environ.get("APP_ENV", os.environ.get("ENVIRONMENT", "dev"))


class Settings(BaseSettings):
    service_name: str = "ugsys-user-profile-service"
    version: str = "0.1.0"
    environment: str = _resolve_environment()
    aws_region: str = "us-east-1"
    dynamodb_table_prefix: str = "ugsys"
    event_bus_name: str = "ugsys-platform-bus"
    log_level: str = "INFO"

    # JWT RS256 — public key only (verify-only, no signing)
    # Set JWT_KEYS_SECRET_ARN to load from Secrets Manager (prod Lambda),
    # or JWT_PUBLIC_KEY + JWT_KEY_ID for local dev / CI.
    jwt_keys_secret_arn: str = ""
    jwt_public_key: str = ""
    jwt_key_id: str = "ugsys-v1"
    jwt_audience: str = "admin-panel"

    # Table name resolved at runtime — matches CDK: ugsys-user-profiles-{env}
    @property
    def profiles_table(self) -> str:
        return f"{self.dynamodb_table_prefix}-user-profiles-{self.environment}"

    @property
    def avatars_bucket_name(self) -> str:
        return f"ugsys-avatars-{self.environment}"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)


settings = Settings()
