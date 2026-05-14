import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up...")

    yield

    container = getattr(app.state, "dishka_container", None)
    if container is not None:
        await container.close()

    logger.info("Shutdown completed")
