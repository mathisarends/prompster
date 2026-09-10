import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_canon import Composition, ErrorOptions, Feature

from backend._logging import setup_logging
from backend.env import EnvSettings, LoggingLevelSettings
from backend.features import (
    auth,
    llm,
    oauth_connections,
    payment,
    session,
    spotify,
    user,
)
from backend.infrastructure.di import (
    DatabaseProvider,
    EmailProvider,
    ObjectStorageProvider,
)
from backend.lifespan import lifespan
from backend.presentation import LoggingMiddleware, health_router

logger = logging.getLogger(__name__)

_FEATURES = (
    auth.feature,
    llm.feature,
    oauth_connections.feature,
    payment.feature,
    spotify.feature,
    session.feature,
    user.feature,
)

_INFRASTRUCTURE_FEATURE = Feature(
    providers=(DatabaseProvider(), EmailProvider(), ObjectStorageProvider()),
)
_SYSTEM_FEATURE = Feature(routers=(health_router,))
_COMPOSITION = Composition(
    _SYSTEM_FEATURE,
    _INFRASTRUCTURE_FEATURE,
    *_FEATURES,
    errors=ErrorOptions(type_base="https://api.prompster.dev/problems"),
)


def _setup_middleware(app: FastAPI, env: EnvSettings) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=env.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(LoggingMiddleware)


def _create_app() -> FastAPI:
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

    _setup_middleware(app, env)
    _COMPOSITION.apply(app)

    logger.info("Application ready!")
    return app


app = _create_app()
