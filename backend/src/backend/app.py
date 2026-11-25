import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_canon import APIRouter, Composition, ErrorOptions, Feature
from starlette.middleware import Middleware

from backend._logging import setup_logging
from backend.env import EnvSettings, LoggingLevelSettings
from backend.features import (
    auth,
    health,
    llm,
    oauth_connections,
    session,
    spotify,
    user,
)
from backend.lifespan import lifespan
from backend.platform.database.di import DATABASE_TABLES, create_database
from backend.platform.database.settings import DatabaseSettings
from backend.platform.storage.di import ObjectStorageProvider
from backend.presentation import LoggingMiddleware

logger = logging.getLogger(__name__)

_FEATURES = (
    auth.feature,
    health.feature,
    llm.feature,
    oauth_connections.feature,
    spotify.feature,
    session.feature,
    user.feature,
)

_PLATFORM_FEATURE = Feature(
    name="platform",
    providers=(ObjectStorageProvider,),
    integrations=(DATABASE_TABLES,),
)


def create_app() -> FastAPI:
    env = EnvSettings()
    setup_logging(LoggingLevelSettings())
    logger.info("Creating FastAPI application...")
    app = FastAPI(
        title="Prompster API",
        description="API for Prompster",
        lifespan=lifespan,
        openapi_url=None if env.is_prod else "/openapi.json",
        docs_url=None if env.is_prod else "/docs",
        redoc_url=None if env.is_prod else "/redoc",
    )

    app.include_router(health.health_router)
    _composition(env).build(app)

    logger.info("Application ready!")
    return app


def _composition(env: EnvSettings) -> Composition:
    return Composition(
        features=(_PLATFORM_FEATURE, *_FEATURES),
        integrations=(create_database(DatabaseSettings()),),
        errors=ErrorOptions(type_base="https://api.prompster.dev/problems"),
        router_factory=lambda: APIRouter(prefix="/api/v1"),
        # Outermost first: request logging wraps CORS.
        middleware=(
            Middleware(LoggingMiddleware),
            Middleware(
                CORSMiddleware,
                allow_origins=env.allowed_origins,
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            ),
        ),
    )
