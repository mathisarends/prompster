import logging

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

    api_v1_router = PascalCaseRouter(prefix="/api/v1")
    app.include_router(api_v1_router)

    logger.info("Application ready!")
    return app


app = _create_app()
