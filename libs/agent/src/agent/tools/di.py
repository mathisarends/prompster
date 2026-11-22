from typing import TYPE_CHECKING, Annotated, Any, Self, final


@final
class ToolContext:
    _marker_instance: InjectMarker | None = None

    if TYPE_CHECKING:
        type Inject[T] = T
    else:

        class Inject:
            def __class_getitem__(cls, item: Any) -> Any:
                return Annotated[item, ToolContext._get_marker()]

    @staticmethod
    def _get_marker() -> InjectMarker:
        if ToolContext._marker_instance is None:
            ToolContext._marker_instance = InjectMarker()
        return ToolContext._marker_instance

    def __init__(self, *dependencies: Any) -> None:
        self._dependencies: list[Any] = list(dependencies)

    def provide(self, *dependencies: Any) -> Self:
        self._dependencies.extend(dependencies)
        return self

    def clear(self) -> Self:
        self._dependencies.clear()
        return self

    def resolve[T](self, expected_type: type[T]) -> T | None:
        for dep in self._dependencies:
            try:
                if isinstance(dep, expected_type):
                    return dep
            except TypeError:
                continue
        return None

    def __len__(self) -> int:
        return len(self._dependencies)


@final
class InjectMarker:
    def __repr__(self) -> str:
        return "ToolContext.Inject"


Inject = ToolContext.Inject
