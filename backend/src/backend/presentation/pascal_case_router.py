from fastapi_canon import CanonRouter


class PascalCaseRouter(CanonRouter):
    """
    A custom APIRouter that ensures response models use alias names (typically PascalCase) in API responses.

    Overrides the `add_api_route` method to set `response_model_by_alias=True` by default,
    so that response model fields are serialized using their alias names rather than their Python attribute names.

    Example:
        If a response model uses PascalCase aliases, the API will return fields in PascalCase.
    """

    def add_api_route(self, *args, **kwargs):
        kwargs.setdefault("response_model_by_alias", True)
        super().add_api_route(*args, **kwargs)
