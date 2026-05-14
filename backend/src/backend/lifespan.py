import logging
from contextlib import asynccontextmanager

from dishka import make_async_container
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI

from backend.features.auth.infrastructure.di import AuthProvider
from backend.features.session.infrastructure.di import SessionProvider


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up...")

    container = make_async_container(
        AuthProvider(),
        SessionProvider(),
    )
    setup_dishka(container, app)

    yield

    await container.close()
    logger.info("Shutdown completed")
