from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from agent.tools.di import Inject
from agent.tools.schema_builder import ToolSchemaBuilder


class _Service:
    pass


class _Kind(str, Enum):
    album = "album"
    single = "single"


class _SearchParams(BaseModel):
    query: str = Field(description="Search text")
    limit: int = Field(default=10, description="Maximum number of results")
    kind: _Kind = Field(default=_Kind.album, description="Requested content kind")


class _ConstrainedOptionsParams(BaseModel):
    options: list[str] = Field(min_length=3, max_length=8)


def _search_signature(
    query: Annotated[str, "Search query"],
    limit: int = 10,
    kinds: list[Literal["album", "single"]] | None = None,
    service: Inject[_Service] = None,
) -> str:
    return f"{query}:{limit}:{kinds}:{service}"


def _search_with_model(params: _SearchParams) -> str:
    return params.query


def _options_with_model(params: _ConstrainedOptionsParams) -> list[str]:
    return params.options


class TestToolSchemaBuilderAbstraction:
    def test_build_uses_function_signature_and_skips_injected_parameters(self) -> None:
        schema = ToolSchemaBuilder(_search_signature).build()

        assert schema["type"] == "object"
        assert schema["required"] == ["query"]
        assert set(schema["properties"].keys()) == {"query", "limit", "kinds"}
        assert schema["properties"]["query"]["description"] == "Search query"
        assert schema["properties"]["limit"]["type"] == "integer"
        assert schema["properties"]["kinds"]["type"] == "array"
        assert schema["properties"]["kinds"]["items"]["enum"] == ["album", "single"]

    def test_build_uses_pydantic_param_model_schema_when_provided(self) -> None:
        schema = ToolSchemaBuilder(
            _search_with_model, param_model=_SearchParams
        ).build()

        assert schema["type"] == "object"
        assert schema["required"] == ["query"]
        assert set(schema["properties"].keys()) == {"query", "limit", "kind"}
        assert schema["properties"]["query"]["description"] == "Search text"
        assert schema["properties"]["limit"]["default"] == 10
        assert schema["properties"]["kind"]["enum"] == ["album", "single"]

    def test_build_includes_pydantic_array_length_constraints(self) -> None:
        schema = ToolSchemaBuilder(
            _options_with_model, param_model=_ConstrainedOptionsParams
        ).build()

        assert schema["properties"]["options"]["minItems"] == 3
        assert schema["properties"]["options"]["maxItems"] == 8
