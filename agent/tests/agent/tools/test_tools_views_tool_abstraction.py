import pytest
from pydantic import BaseModel

from agent.tools.views import Tool


class _Params(BaseModel):
    query: str
    limit: int = 10


async def _async_returns_none() -> None:
    return None


def _sync_returns_none() -> None:
    return None


def _read_query(params: _Params) -> str:
    return params.query


class TestToolAbstraction:
    def test_rejects_status_and_status_label_together(self) -> None:
        with pytest.raises(ValueError, match="both 'status' and 'status_label'"):
            Tool(
                name="demo",
                description="Demo",
                fn=_read_query,
                status="Busy",
                status_label="Busy",
            )

    def test_status_label_callable_requires_param_model(self) -> None:
        with pytest.raises(ValueError, match="requires a params model"):
            Tool(
                name="demo",
                description="Demo",
                fn=_sync_returns_none,
                status_label=lambda params: f"query={params.query}",
            )

    def test_status_label_callable_rejects_unknown_field(self) -> None:
        with pytest.raises(ValueError, match="unknown params-model field"):
            Tool(
                name="demo",
                description="Demo",
                fn=_read_query,
                status_label=lambda params: params.unknown,
                param_model=_Params,
            )

    def test_status_label_callable_must_return_string(self) -> None:
        with pytest.raises(ValueError, match="must return str"):
            Tool(
                name="demo",
                description="Demo",
                fn=_read_query,
                status_label=lambda params: 123,
                param_model=_Params,
            )

    def test_render_status_callable_with_valid_args(self) -> None:
        tool = Tool(
            name="demo",
            description="Demo",
            fn=_read_query,
            status_label=lambda params: f"Searching: {params.query}",
            param_model=_Params,
        )

        status = tool.render_status({"query": "abba"})

        assert status == "Searching: abba"

    def test_render_status_returns_none_for_invalid_args(self) -> None:
        tool = Tool(
            name="demo",
            description="Demo",
            fn=_read_query,
            status_label=lambda params: f"Searching: {params.query}",
            param_model=_Params,
        )

        status = tool.render_status({"limit": 3})

        assert status is None

    @pytest.mark.asyncio
    async def test_execute_async_none_becomes_empty_string(self) -> None:
        tool = Tool(name="demo", description="Demo", fn=_async_returns_none)

        result = await tool.execute({})

        assert result == ""

    @pytest.mark.asyncio
    async def test_execute_sync_none_becomes_empty_string(self) -> None:
        tool = Tool(name="demo", description="Demo", fn=_sync_returns_none)

        result = await tool.execute({})

        assert result == ""

    def test_to_schema_uses_explicit_schema_if_provided(self) -> None:
        explicit_schema = {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        }
        tool = Tool(
            name="demo",
            description="Demo",
            fn=_read_query,
            schema=explicit_schema,
            param_model=_Params,
        )

        schema = tool.to_schema()

        assert schema["function"]["parameters"] == explicit_schema

    def test_format_error_prefixes_exception_message(self) -> None:
        tool = Tool(
            name="demo", description="Demo", fn=_read_query, param_model=_Params
        )

        error_text = tool.format_error(RuntimeError("boom"))

        assert error_text == "Error: boom"
