"""Composition root — wires all dependencies and starts the FastAPI app."""

import json
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import aioboto3
import boto3
import structlog
from fastapi import FastAPI
from mangum import Mangum

from src.config import settings
from src.domain.exceptions import DomainError
from src.infrastructure.adapters.s3_avatar_storage import S3AvatarStorage
from src.infrastructure.logging import configure_logging
from src.infrastructure.messaging.event_publisher import EventBridgePublisher
from src.infrastructure.persistence.dynamodb_profile_repository import (
    DynamoDBProfileRepository,
)
from src.presentation.api.v1 import health, plugin_manifest, profiles
from src.presentation.middleware.correlation_id import CorrelationIdMiddleware
from src.presentation.middleware.exception_handler import (
    domain_exception_handler,
    unhandled_exception_handler,
)
from src.presentation.middleware.rate_limiting import RateLimitMiddleware
from src.presentation.middleware.security_headers import SecurityHeadersMiddleware

configure_logging(settings.service_name, settings.log_level)
logger = structlog.get_logger()


def _resolve_jwt_public_key() -> tuple[str, str]:
    """Return (public_key_pem, key_id) — from env vars or Secrets Manager."""
    if settings.jwt_public_key:
        return settings.jwt_public_key, settings.jwt_key_id

    if settings.jwt_keys_secret_arn:
        client = boto3.client("secretsmanager", region_name=settings.aws_region)
        response = client.get_secret_value(SecretId=settings.jwt_keys_secret_arn)
        parsed: dict[str, str] = json.loads(response.get("SecretString", "{}"))
        return parsed["public_key"], parsed.get("key_id", "ugsys-v1")

    raise RuntimeError(
        "JWT public key not configured. "
        "Set JWT_KEYS_SECRET_ARN (prod) or JWT_PUBLIC_KEY + JWT_KEY_ID (dev/CI)."
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    logger.info("startup.begin", service=settings.service_name, version=settings.version)
    yield
    logger.info("shutdown.complete", service=settings.service_name)


def create_app() -> FastAPI:
    """Application factory — single place for all wiring."""
    app = FastAPI(
        title=settings.service_name,
        version=settings.version,
        docs_url=None if settings.environment == "prod" else "/docs",
        lifespan=lifespan,
    )

    # Middleware — last added = first executed
    app.add_middleware(CorrelationIdMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RateLimitMiddleware)

    # Exception handlers — registered before routers
    app.add_exception_handler(DomainError, domain_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unhandled_exception_handler)

    # Shared aioboto3 session
    _session = aioboto3.Session()

    # Wire infrastructure
    _repo = DynamoDBProfileRepository(
        table_name=settings.profiles_table,
        region=settings.aws_region,
        session=_session,
    )
    _avatar_storage = S3AvatarStorage(
        bucket_name=settings.avatars_bucket_name,
        region=settings.aws_region,
        session=_session,
    )
    _publisher = EventBridgePublisher(
        event_bus_name=settings.event_bus_name,
        region=settings.aws_region,
        session=_session,
    )

    # Wire application service
    from src.application.services.profile_service import ProfileService

    _profile_service = ProfileService(
        profile_repo=_repo,
        event_publisher=_publisher,
        avatar_storage=_avatar_storage,
    )

    # Wire JWT token service (verify-only — public key only, no signing)
    from src.infrastructure.adapters.jwt_token_service import JWTTokenService

    _public_key, _key_id = _resolve_jwt_public_key()
    _token_service = JWTTokenService(
        private_key="",  # not needed — this service only verifies, never signs
        public_key=_public_key,
        key_id=_key_id,
        audience=settings.jwt_audience,
    )

    # Inject into routers
    app.dependency_overrides[profiles.get_profile_service] = lambda: _profile_service
    app.dependency_overrides[profiles.get_token_service] = lambda: _token_service

    # Routers
    app.include_router(health.router)
    app.include_router(plugin_manifest.router)
    app.include_router(profiles.router, prefix="/api/v1")

    return app


app = create_app()

# Lambda handler
handler = Mangum(app)
