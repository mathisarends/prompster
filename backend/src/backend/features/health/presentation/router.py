from fastapi import status
from fastapi_canon import APIRouter, Inject

from backend.features.health.application import ReadinessCheck
from backend.features.health.presentation.errors import (
    SERVICE_NOT_READY_ERROR,
)
from backend.features.health.presentation.schemas import (
    HealthResponse,
    ReadinessResponse,
)

health_router = APIRouter(
    tags=["system"],
)


@health_router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    operation_id="health_check",
)
async def health_check() -> HealthResponse:
    return HealthResponse()


@health_router.get(
    "/readiness",
    response_model=ReadinessResponse,
    status_code=status.HTTP_200_OK,
    operation_id="readiness_check",
    raises=(SERVICE_NOT_READY_ERROR,),
)
async def readiness_check(
    readiness: Inject[ReadinessCheck],
) -> ReadinessResponse:
    await readiness.check()
    return ReadinessResponse()
