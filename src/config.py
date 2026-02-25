"""Service configuration — loaded from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    service_name: str = "ugsys-user-profile-service"
    version: str = "0.1.0"
    environment: str = "dev"
    aws_region: str = "us-east-1"
    dynamodb_table_prefix: str = "ugsys"
    event_bus_name: str = "ugsys-platform-bus"
    log_level: str = "INFO"

    # Table name resolved at runtime
    @property
    def profiles_table(self) -> str:
        return f"{self.dynamodb_table_prefix}-profiles-{self.environment}"

    @property
    def avatars_bucket_name(self) -> str:
        return f"ugsys-avatars-{self.environment}"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)


settings = Settings()
