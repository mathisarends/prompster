import pytest
from pydantic import BaseModel

from agent.tools.params import ToolParams
from agent.tools.views import ActionResult, ActionType, Phase, Tool


class _Params(BaseModel):
    query: str
    limit: int = 10


async def _async_returns_empty_result() -> ActionResult:
    return ActionResult(success=True, extracted_content="")


def _sync_returns_empty_result() -> ActionResult:
    return ActionResult(success=True, extracted_content="")


def _read_query(params: _Params) -> str:
    return params.query


class TestToolAbstraction:
    def test_tool_params_requires_status_field(self) -> None:
        class _Concrete(ToolParams):
            query: str

        with pytest.raises(ValueError, match="status"):
            _Concrete.model_validate({"query": "abba"})

    def test_tool_params_accepts_status_field(self) -> None:
        class _Concrete(ToolParams):
            query: str

        params = _Concrete.model_validate({"query": "abba", "status": "Suche läuft"})

        assert params.status == "Suche läuft"
        assert params.query == "abba"

    def test_action_result_requires_string_extracted_content(self) -> None:
        with pytest.raises(ValueError, match="valid string"):
            ActionResult(success=True, extracted_content={"value": 1})

    def test_render_status_returns_lambda_result(self) -> None:
        class _Concrete(ToolParams):
            query: str

        tool = Tool(
            name="demo",
            description="Demo",
            fn=lambda params: params.query,
            param_model=_Concrete,
            status_label=lambda params: params.status,
        )

        assert (
            tool.render_status({"query": "abba", "status": "Suche nach 'abba'"})
            == "Suche nach 'abba'"
        )

    def test_render_status_returns_none_for_invalid_args(self) -> None:
        class _Concrete(ToolParams):
            query: str

        tool = Tool(
            name="demo",
            description="Demo",
            fn=lambda params: params.query,
            param_model=_Concrete,
            status_label=lambda params: params.status,
        )

        assert tool.render_status({"query": "abba"}) is None

    @pytest.mark.asyncio
    async def test_execute_async_none_becomes_empty_string(self) -> None:
        tool = Tool(name="demo", description="Demo", fn=_async_returns_empty_result)

        result = await tool.execute({})

        assert result == ActionResult(success=True, extracted_content="")

    @pytest.mark.asyncio
    async def test_execute_sync_none_becomes_empty_string(self) -> None:
        tool = Tool(name="demo", description="Demo", fn=_sync_returns_empty_result)

        result = await tool.execute({})

        assert result == ActionResult(success=True, extracted_content="")

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

    @pytest.mark.asyncio
    async def test_execute_propagates_exception_from_tool_handler(self) -> None:
        async def _explode() -> None:
            raise RuntimeError("boom")

        tool = Tool(
            name="demo",
            description="Demo",
            fn=_explode,
        )

        with pytest.raises(RuntimeError, match="boom"):
            await tool.execute({})

    @pytest.mark.asyncio
    async def test_execute_raises_when_handler_does_not_return_action_result(
        self,
    ) -> None:
        async def _invalid() -> str:
            return "not-an-action-result"

        tool = Tool(name="demo", description="Demo", fn=_invalid)

        with pytest.raises(TypeError, match="must return ActionResult"):
            await tool.execute({})

    def test_action_type_defaults_to_none(self) -> None:
        tool = Tool(name="demo", description="Demo", fn=_sync_returns_empty_result)

        assert tool.action_type is None

    def test_action_type_can_be_overridden(self) -> None:
        tool = Tool(
            name="demo",
            description="Demo",
            fn=_sync_returns_empty_result,
            action_type=ActionType.SEARCH_TRACKS,
        )

        assert tool.action_type == ActionType.SEARCH_TRACKS

    def test_tool_without_phase_metadata_is_included_in_all_phases(self) -> None:
        tool = Tool(name="demo", description="Demo", fn=_sync_returns_empty_result)

        assert tool.included_in_phases == frozenset()
        assert tool.is_included_in(Phase.ONBOARDING) is True
        assert tool.is_included_in(Phase.BUILD) is True

    def test_tool_can_be_limited_to_explicit_phases(self) -> None:
        tool = Tool(
            name="demo",
            description="Demo",
            fn=_sync_returns_empty_result,
            included_in_phases={Phase.BUILD},
        )

        assert tool.included_in_phases == frozenset({Phase.BUILD})
        assert tool.is_included_in(Phase.ONBOARDING) is False
        assert tool.is_included_in(Phase.BUILD) is True
