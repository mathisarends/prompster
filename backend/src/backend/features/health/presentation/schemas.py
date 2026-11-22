from typing import Literal

from backend.presentation import Schema


class HealthResponse(Schema):
    status: Literal["ok"] = "ok"


class ReadinessResponse(Schema):
    status: Literal["ready"] = "ready"
