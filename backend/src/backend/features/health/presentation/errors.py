from fastapi import status
from fastapi_canon import Error

from backend.features.health.domain import ServiceNotReadyError

SERVICE_NOT_READY_ERROR = Error(
    ServiceNotReadyError,
    status=status.HTTP_503_SERVICE_UNAVAILABLE,
    code="service_not_ready",
)

HEALTH_ERRORS = (SERVICE_NOT_READY_ERROR,)
