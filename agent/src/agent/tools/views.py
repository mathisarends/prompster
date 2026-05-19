import inspect
from collections.abc import Callable
from typing import Any, overload

from pydantic import BaseModel

from agent.tools.schema_builder import ToolSchemaBuilder
from agent.tools.schemas import ToolSchema


class Tool:
    @overload
    def __init__[P: BaseModel](
        self,
        name: str,
        description: str,
        fn: Callable[..., Any],
        status: str | Callable[[P], str] | None = None,
        status_label: str | Callable[[P], str] | None = None,
        schema: dict | None = None,
        param_model: type[P] = ...,
    ) -> None: ...

    @overload
    def __init__(
        self,
        name: str,
        description: str,
        fn: Callable[..., Any],
        status: str | None = None,
        status_label: str | None = None,
        schema: dict | None = None,
        param_model: None = None,
    ) -> None: ...

    def __init__(
        self,
        name: str,
        description: str,
        fn: Callable[..., Any],
        status: str | Callable[[BaseModel], str] | None = None,
        status_label: str | Callable[[BaseModel], str] | None = None,
        schema: dict | None = None,
        param_model: type[BaseModel] | None = None,
    ) -> None:
        if status is not None and status_label is not None:
            raise ValueError(
                f"Tool '{name}' received both 'status' and 'status_label'. Use only one."
            )

        self.name = name
        self.description = description
        self.fn = fn
        self._schema = schema
        self.param_model = param_model
        self._schema_builder = (
            None if schema else ToolSchemaBuilder(self.fn, param_model)
        )
        self._status_label = status_label if status_label is not None else status

        if callable(self._status_label):
            if self.param_model is None:
                raise ValueError(
                    f"Tool '{self.name}' status_label callable requires a params model"
                )
            self._validate_status_label_for_model()

    def _validate_status_label_for_model(self) -> None:
        assert self.param_model is not None
        assert callable(self._status_label)

        dummy = _make_dummy(self.param_model)
        try:
            result = self._status_label(dummy)
            if not isinstance(result, str):
                raise ValueError(
                    f"Tool '{self.name}' status_label callable must return str, "
                    f"got {type(result).__name__}"
                )
        except AttributeError as error:
            raise ValueError(
                f"Tool '{self.name}' status_label callable references unknown params-model field: {error}"
            ) from error
        except ValueError:
            raise
        except Exception:
            pass

    def render_status(self, args: dict[str, Any]) -> str | None:
        if self._status_label is None:
            return None
        if callable(self._status_label):
            if self.param_model is None:
                return None
            try:
                params = self.param_model.model_validate(args)
                return self._status_label(params)
            except Exception:
                return None
        return self._status_label

    async def execute(self, args: dict[str, Any]) -> Any:
        if inspect.iscoroutinefunction(self.fn):
            result = await self.fn(**args)
        else:
            result = self.fn(**args)
        return result if result is not None else ""

    def format_error(self, error: Exception) -> str:
        return f"Error: {error}"

    def to_schema(self) -> ToolSchema:
        parameters = self._schema if self._schema else self._schema_builder.build()
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": parameters,
            },
        }

    def __eq__(self, other: object) -> bool:
        return self.name == other.name if isinstance(other, Tool) else NotImplemented

    def __hash__(self) -> int:
        return hash(self.name)


def _make_dummy(param_model: type[BaseModel]) -> BaseModel:
    type_defaults: dict[type, Any] = {
        str: "placeholder",
        int: 0,
        float: 0.0,
        bool: False,
    }
    defaults = {
        field_name: type_defaults.get(field_info.annotation, None)
        for field_name, field_info in param_model.model_fields.items()
    }
    return param_model.model_construct(**defaults)
