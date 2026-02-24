"""Composition root — wires all dependencies and starts the FastAPI app."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from mangum import Mangum

from src.application.services.profile_service import ProfileService
from src.config import settings
from src.infrastructure.logging import configure_logging
from src.infrastructure.messaging.event_publisher import EventBridgePublisher
from src.infrastructure.persistence.dynamodb_profile_repository import (
    DynamoDBProfileRepository,
)
from src.presentation.api.v1 import health, profiles
from src.presentation.middleware.correlation_id import CorrelationIdMiddleware
from src.presentation.middleware.rate_limiting import RateLimitMiddleware
from src.presentation.middleware.security_headers import SecurityHeadersMiddleware

configure_logging(settings.service_name, settings.log_level)
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    logger.info("startup", service=settings.service_name, env=settings.environment)
    yield
    logger.info("shutdown", service=settings.service_name)


app = FastAPI(
    title="ugsys-user-profile-service",
    version="0.1.0",
    lifespan=lifespan,
)

# Middleware (order matters — outermost first)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(CorrelationIdMiddleware)

# Wire dependencies
_repo = DynamoDBProfileRepository(
    table_name=settings.profiles_table,
    region=settings.aws_region,
)
_publisher = EventBridgePublisher(
    event_bus_name=settings.event_bus_name,
    region=settings.aws_region,
)
_profile_service = ProfileService(profile_repo=_repo, event_publisher=_publisher)

# Inject into routers
app.dependency_overrides[profiles.get_profile_service] = lambda: _profile_service

# Routers
app.include_router(health.router)
app.include_router(profiles.router, prefix="/api/v1")

# Lambda handler
handler = Mangum(app)
