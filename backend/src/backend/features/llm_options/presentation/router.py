from fastapi import APIRouter, status
from llm import LLMProvider
from llm.registry import DEFAULT_OPENAI_MODEL, OPENAI_MODELS

from backend.features.llm_options.presentation.schemas import (
    LLMOptionResponse,
    LLMOptionsResponse,
)

router = APIRouter(prefix="/llm-options", tags=["llm-options"])


@router.get(
    "",
    response_model=LLMOptionsResponse,
    status_code=status.HTTP_200_OK,
    operation_id="list_llm_options",
)
async def list_llm_options() -> LLMOptionsResponse:
    return LLMOptionsResponse(
        items=[
            LLMOptionResponse(
                id=model.value,
                provider=LLMProvider.OPENAI,
                label=model.value,
                is_default=model == DEFAULT_OPENAI_MODEL,
            )
            for model in OPENAI_MODELS
        ]
    )
