import logging
from collections.abc import Callable
from typing import Any, overload

from pydantic import BaseModel

from agent.tools.di import ToolContext
from agent.tools.executor import ToolExecutor
from agent.tools.schemas import ToolSchema
from agent.tools.views import Tool

logger = logging.getLogger(__name__)


class Tools:
    def __init__(
        self,
        context: ToolContext | None = None,
    ) -> None:
        self._tools: dict[str, Tool] = {}
        self._context = context if context is not None else ToolContext()
        self._executor = ToolExecutor(self._tools, self._context)

        self._register_default_tools()

    def set_context(self, context: ToolContext) -> None:
        self._context = context
        self._executor.set_context(context)

    def get_context(self) -> ToolContext:
        return self._context

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    @overload
    def action[P: BaseModel](
        self,
        description: str,
        name: str | None = None,
        *,
        status: str | Callable[[P], str] | None = None,
        status_label: str | Callable[[P], str] | None = None,
        params: type[P],
    ) -> Callable: ...

    @overload
    def action(
        self,
        description: str,
        name: str | None = None,
        *,
        status: str | None = None,
        status_label: str | None = None,
        params: None = None,
    ) -> Callable: ...

    def action[P: BaseModel](
        self,
        description: str,
        name: str | None = None,
        status: str | Callable[[P], str] | None = None,
        status_label: str | Callable[[P], str] | None = None,
        params: type[P] | None = None,
    ) -> Callable:
        if status is not None and status_label is not None:
            raise ValueError("Use either 'status' or 'status_label', not both")

        def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
            self._register(
                Tool(
                    name=name or fn.__name__,
                    description=description,
                    fn=fn,
                    status=status,
                    status_label=status_label,
                    param_model=params,
                )
            )
            return fn

        return decorator

    def _register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    async def execute(self, name: str, args: dict) -> Any:
        return await self._executor.execute(name, args)

    def to_schema(self) -> list[ToolSchema]:
        return [t.to_schema() for t in self._tools.values()]

    def render_status(self, name: str, args: dict[str, Any]) -> str | None:
        tool = self.get(name)
        if tool is None:
            raise ValueError(f"Unknown tool '{name}'. Available: {list(self._tools)}")
        return tool.render_status(args)
