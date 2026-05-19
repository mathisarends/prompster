import pytest
from pydantic import BaseModel

from agent.tools.di import Inject, ToolContext
from agent.tools.executor import ToolExecutor
from agent.tools.views import Tool


class _Service:
    def __init__(self, prefix: str) -> None:
        self.prefix = prefix


class _Params(BaseModel):
    value: int


async def _combine(service: Inject[_Service], params: _Params) -> str:
    return f"{service.prefix}:{params.value}"


async def _explode(params: _Params) -> str:
    raise RuntimeError("boom")


async def _optional_injected(params: _Params, service: Inject[_Service] = None) -> str:
    prefix = service.prefix if service is not None else "none"
    return f"{prefix}:{params.value}"


async def _invalid_param_target(first: str, second: str) -> str:
    return f"{first}:{second}"


class TestToolExecutorAbstraction:
    @pytest.mark.asyncio
    async def test_execute_resolves_injected_dependency_and_param_model(self) -> None:
        tool = Tool(
            name="combine",
            description="Combine",
            fn=_combine,
            param_model=_Params,
        )
        executor = ToolExecutor({"combine": tool}, ToolContext(_Service("svc")))

        result = await executor.execute("combine", {"value": 7})

        assert result == "svc:7"

    @pytest.mark.asyncio
    async def test_execute_unknown_tool_raises_value_error(self) -> None:
        executor = ToolExecutor({}, ToolContext())

        with pytest.raises(ValueError, match="Unknown tool 'missing'"):
            await executor.execute("missing", {})

    @pytest.mark.asyncio
    async def test_execute_returns_formatted_error_when_tool_raises(self) -> None:
        tool = Tool(
            name="explode",
            description="Explode",
            fn=_explode,
            param_model=_Params,
        )
        executor = ToolExecutor({"explode": tool}, ToolContext())

        result = await executor.execute("explode", {"value": 1})

        assert result == "Error: boom"

    @pytest.mark.asyncio
    async def test_execute_returns_error_when_required_injected_dep_missing(
        self,
    ) -> None:
        tool = Tool(
            name="combine",
            description="Combine",
            fn=_combine,
            param_model=_Params,
        )
        executor = ToolExecutor({"combine": tool}, ToolContext())

        result = await executor.execute("combine", {"value": 4})

        assert "Missing injected dependency" in result
        assert "service" in result

    @pytest.mark.asyncio
    async def test_execute_uses_default_for_optional_injected_dep(self) -> None:
        tool = Tool(
            name="optional",
            description="Optional",
            fn=_optional_injected,
            param_model=_Params,
        )
        executor = ToolExecutor({"optional": tool}, ToolContext())

        result = await executor.execute("optional", {"value": 9})

        assert result == "none:9"

    @pytest.mark.asyncio
    async def test_execute_returns_error_when_param_model_has_no_target_parameter(
        self,
    ) -> None:
        tool = Tool(
            name="invalid",
            description="Invalid",
            fn=_invalid_param_target,
            param_model=_Params,
        )
        executor = ToolExecutor({"invalid": tool}, ToolContext())

        result = await executor.execute("invalid", {"value": 3})

        assert "has no parameter that can receive it" in result
