from fastapi import status
from fastapi_canon import Error

from backend.features.health.application import ServiceNotReadyException

SERVICE_NOT_READY_ERROR = Error(
    ServiceNotReadyException,
    status=status.HTTP_503_SERVICE_UNAVAILABLE,
    code="service_not_ready",
)

HEALTH_ERRORS = (
    SERVICE_NOT_READY_ERROR,
)
