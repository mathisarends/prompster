from backend.features.llm.configuration import LLMRegistry
from backend.features.llm.presentation.schemas import (
    LLMCapabilitiesResponse,
    LLMDefaultsResponse,
    LLMOptionResponse,
    LLMOptionsResponse,
)
from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, status

router = APIRouter(
    route_class=DishkaRoute,
    prefix="/llm-options",
    tags=["llm-options"],
)


@router.get(
    "",
    response_model=LLMOptionsResponse,
    status_code=status.HTTP_200_OK,
    operation_id="list_llm_options",
)
async def list_llm_options(
    registry: FromDishka[LLMRegistry],
) -> LLMOptionsResponse:
    return LLMOptionsResponse(
        items=[
            LLMOptionResponse(
                id=model.id,
                provider=model.provider,
                label=model.presentation.label,
                profile=model.presentation.profile,
                capabilities=LLMCapabilitiesResponse(
                    temperature=model.capabilities.temperature,
                    reasoning_effort=list(model.capabilities.reasoning_effort),
                ),
                defaults=LLMDefaultsResponse(
                    reasoning_effort=model.defaults.reasoning_effort,
                ),
                is_default=model.id == registry.default_model.id,
            )
            for model in registry.available_models
        ]
    )
