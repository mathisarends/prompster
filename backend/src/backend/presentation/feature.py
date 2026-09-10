from collections.abc import Sequence

from fastapi import APIRouter
from fastapi_canon import ErrorRegistry, Feature, ProviderSource


def api_feature(
    *,
    name: str,
    routers: Sequence[APIRouter] = (),
    providers: Sequence[ProviderSource] = (),
    errors: ErrorRegistry | None = None,
) -> Feature:
    """Build one versioned API feature for the application composition."""
    return Feature(
        name=name,
        routers=routers,
        providers=providers,
        errors=errors,
    )
