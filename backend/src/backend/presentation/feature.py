from collections.abc import Sequence

from dishka import Provider
from fastapi import APIRouter
from fastapi_canon import ErrorRegistry, Feature

from backend.presentation.pascal_case_router import PascalCaseRouter


def api_feature(
    *,
    routers: Sequence[APIRouter] = (),
    providers: Sequence[type[Provider]] = (),
    errors: ErrorRegistry | None = None,
) -> Feature:
    """Build one versioned API feature for the application composition."""
    api_router = PascalCaseRouter(prefix="/api/v1")
    for router in routers:
        api_router.include_router(router)

    return Feature(
        routers=(api_router,),
        providers=tuple(provider() for provider in providers),
        errors=errors,
    )
