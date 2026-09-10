import logging

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger(__name__)

health_router = APIRouter(route_class=DishkaRoute, tags=["system"])


@health_router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    operation_id="health_check",
)
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@health_router.get(
    "/readiness",
    response_model=None,
    status_code=status.HTTP_200_OK,
    operation_id="readiness_check",
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "The application is not ready to receive traffic.",
            "x-fastapi-canon-errors": [],
            "content": {
                "application/json": {
                    "example": {"status": "not_ready"},
                }
            },
        },
    },
)
async def readiness_check(
    engine: FromDishka[AsyncEngine],
) -> dict[str, str] | JSONResponse:
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except Exception:
        logger.warning("Readiness check failed", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not_ready"},
        )

    return {"status": "ready"}
