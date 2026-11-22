from fastapi import status
from fastapi_canon import APIRouter, Inject

from backend.features.llm.domain import LLMRegistry
from backend.features.llm.presentation.schemas import (
    LLMCapabilitiesResponse,
    LLMDefaultsResponse,
    LLMOptionResponse,
    LLMOptionsResponse,
)

router = APIRouter(
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
    registry: Inject[LLMRegistry],
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
