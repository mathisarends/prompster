import inspect
from collections.abc import Callable, Iterable
from enum import StrEnum
from typing import Any, Self

from pydantic import BaseModel, Field

from agent.tools.schema_builder import ToolSchemaBuilder
from agent.tools.schemas import ToolSchema


class ActionType(StrEnum):
    ASK_ONBOARDING_QUESTION = "ask_onboarding_question"
    SEARCH_TRACKS = "search_tracks"
    SEARCH_PLAYLISTS = "search_playlists"
    ADD_DECK_TRACKS = "add_deck_tracks"
    REMOVE_DECK_TRACKS = "remove_deck_tracks"
    REPLACE_DECK_TRACKS = "replace_deck_tracks"
    GET_SPOTIFY_PLAYLIST_TRACKS = "get_spotify_playlist_tracks"
    SELF_REVIEW = "self_review"


class Phase(StrEnum):
    ONBOARDING = "onboarding"
    BUILD = "build"


class OnboardingSelectionMode(StrEnum):
    SINGLE_SELECT = "single_select"
    MULTI_SELECT = "multi_select"


class InputRequest(BaseModel):
    question: str
    hint: str | None = None
    options: list[str] = Field(default_factory=list)
    recommended_option: str | None = None
    selection_mode: OnboardingSelectionMode = OnboardingSelectionMode.SINGLE_SELECT
    is_last_question: bool = False


class ActionResult(BaseModel):
    success: bool
    extracted_content: str = ""
    error: str | None = None
    input_request: InputRequest | None = None

    @classmethod
    def ok(
        cls,
        extracted_content: str = "",
        *,
        input_request: InputRequest | None = None,
    ) -> Self:
        return cls(
            success=True,
            extracted_content=extracted_content,
            input_request=input_request,
        )

    @classmethod
    def fail(cls, error: Exception | str) -> Self:
        return cls(success=False, extracted_content="", error=str(error))

    def to_content(self) -> str:
        return self.extracted_content if self.success else f"Error: {self.error}"


class Tool:
    def __init__(
        self,
        name: str,
        description: str | None,
        fn: Callable[..., Any],
        status_label: Callable[[Any], str] | None = None,
        action_type: ActionType | None = None,
        included_in_phases: Iterable[Phase] | None = None,
        is_onboarding_question: bool = False,
        schema: dict | None = None,
        param_model: type[BaseModel] | None = None,
    ) -> None:
        self.name = name
        self.description = description
        self.fn = fn
        self.action_type = action_type
        self.included_in_phases = frozenset(included_in_phases or ())
        self.is_onboarding_question = is_onboarding_question
        self._schema = schema
        self.param_model = param_model
        self._status_label = status_label
        self._schema_builder = (
            None if schema else ToolSchemaBuilder(self.fn, param_model)
        )

    def is_included_in(self, phase: Phase) -> bool:
        return not self.included_in_phases or phase in self.included_in_phases

    def render_status(self, args: dict[str, Any]) -> str | None:
        if self._status_label is None or self.param_model is None:
            return None
        try:
            params = self.param_model.model_validate(args)
        except Exception:
            return None
        return self._status_label(params)

    async def execute(self, args: dict[str, Any]) -> ActionResult:
        if inspect.iscoroutinefunction(self.fn):
            result = await self.fn(**args)
        else:
            result = self.fn(**args)

        if not isinstance(result, ActionResult):
            raise TypeError(
                f"Tool '{self.name}' must return ActionResult, "
                f"received {type(result).__name__}"
            )
        return result

    def to_schema(self) -> ToolSchema:
        parameters = self._schema if self._schema else self._schema_builder.build()
        function: dict[str, Any] = {
            "name": self.name,
            "parameters": parameters,
        }
        if self.description is not None:
            function["description"] = self.description
        return {
            "type": "function",
            "function": function,
        }

    def __eq__(self, other: object) -> bool:
        return self.name == other.name if isinstance(other, Tool) else NotImplemented

    def __hash__(self) -> int:
        return hash(self.name)
