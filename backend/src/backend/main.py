import logging

from dishka import make_async_container
from dishka.integrations.fastapi import setup_dishka
from backend.features.auth.presentation import (
    auth_router,
    register_auth_exception_handlers,
)
from backend.features.auth.infrastructure.di import AuthProvider
from backend.features.oauth_connections.infrastructure.di import (
    OAuthConnectionsProvider,
)
from backend.features.oauth_connections.presentation import (
    register_oauth_connections_exception_handlers,
    spotify_oauth_router,
)
from backend.features.spotify.infrastructure.di import SpotifyProvider
from backend.features.spotify.presentation import spotify_router
from backend.features.transcription.infrastructure import TranscriptionProvider
from backend.features.transcription.presentation import transcription_router
from backend.features.session.presentation import (
    register_session_exception_handlers,
    router as session_router,
)
from backend.features.session.infrastructure.di import SessionProvider
from backend.features.user.presentation import user_router
from backend.features.user.infrastructure.di import UserProvider
from backend.infrastructure.di import DatabaseProvider, StorageBackendProvider
from backend.presentation import PascalCaseRouter, LoggingMiddleware
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.env import EnvSettings
from backend.lifespan import lifespan

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)


def _setup_middleware(app: FastAPI) -> None:
    env = EnvSettings()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=env.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(LoggingMiddleware)


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

    _setup_middleware(app)
    register_auth_exception_handlers(app)
    register_oauth_connections_exception_handlers(app)
    register_session_exception_handlers(app)

    container = make_async_container(
        DatabaseProvider(),
        StorageBackendProvider(),
        AuthProvider(),
        OAuthConnectionsProvider(),
        SpotifyProvider(),
        TranscriptionProvider(),
        SessionProvider(),
        UserProvider(),
    )
    setup_dishka(container, app)
    app.state.dishka_container = container

    api_v1_router = PascalCaseRouter(prefix="/api/v1")
    api_v1_router.include_router(auth_router)
    api_v1_router.include_router(spotify_oauth_router)
    api_v1_router.include_router(spotify_router)
    api_v1_router.include_router(transcription_router)
    api_v1_router.include_router(session_router)
    api_v1_router.include_router(user_router)
    app.include_router(api_v1_router)

    logger.info("Application ready!")
    return app


app = _create_app()
