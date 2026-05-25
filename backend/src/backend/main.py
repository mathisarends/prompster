import logging

from dishka import make_async_container
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.env import EnvSettings
from backend.features import (
    auth,
    llm_options,
    oauth_connections,
    session,
    spotify,
    transcription,
    user,
)
from backend.infrastructure.di import DatabaseProvider, StorageBackendProvider
from backend.lifespan import lifespan
from backend.presentation import LoggingMiddleware, PascalCaseRouter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)

_FEATURES = [
    auth.feature,
    llm_options.feature,
    oauth_connections.feature,
    spotify.feature,
    transcription.feature,
    session.feature,
    user.feature,
]

_INFRASTRUCTURE_PROVIDERS = [DatabaseProvider, StorageBackendProvider]


def _setup_middleware(app: FastAPI, env: EnvSettings) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=env.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(LoggingMiddleware)


def _register_features(app: FastAPI) -> None:
    api_v1_router = PascalCaseRouter(prefix="/api/v1")
    for feature in _FEATURES:
        if feature.register_exception_handlers is not None:
            feature.register_exception_handlers(app)
        for router in feature.routers:
            api_v1_router.include_router(router)
    app.include_router(api_v1_router)


def _create_container():
    providers = [provider() for provider in _INFRASTRUCTURE_PROVIDERS]
    for feature in _FEATURES:
        providers.extend(provider() for provider in feature.providers)
    return make_async_container(*providers)


def _create_app() -> FastAPI:
    logger.info("Creating FastAPI application...")
    env = EnvSettings()
    app = FastAPI(
        title="Prompster API",
        description="API for Prompster",
        lifespan=lifespan,
        openapi_url=None if env.is_prod else "/openapi.json",
        docs_url=None if env.is_prod else "/docs",
        redoc_url=None if env.is_prod else "/redoc",
    )

    _setup_middleware(app, env)
    _register_features(app)

    container = _create_container()
    setup_dishka(container, app)
    app.state.dishka_container = container

    logger.info("Application ready!")
    return app


app = _create_app()
