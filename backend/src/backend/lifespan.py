import logging
from contextlib import asynccontextmanager

from dishka import make_async_container
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up...")

    container = make_async_container(
        # add providers here if needed
    )
    setup_dishka(container, app)

    yield

    await container.close()
    logger.info("Shutdown completed")
