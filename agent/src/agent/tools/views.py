import inspect
from collections.abc import Callable
from enum import StrEnum
from typing import Any, Self
from uuid import UUID

from agent.playlist import TrackRef, TrackRefReplacement
from pydantic import BaseModel, Field

from agent.tools.schema_builder import ToolSchemaBuilder
from agent.tools.schemas import ToolSchema


class ActionType(StrEnum):
    SEARCH = "search"
    FETCH = "fetch"
    MUTATE = "mutate"
    INTERACT = "interact"


class ToolParams(BaseModel):
    status: str = Field(
        description=(
            "Kurzes deutsches Status-Label im Präsens (max. ~50 Zeichen), das dem "
            "Nutzer anzeigt, was du gerade tust. Beispiele: \"Suche nach 'Abba'\", "
            '"Album-Tracks laden", "Playlist-Entwurf bauen: \'80er Party\'".'
        ),
    )


class ActionResult(BaseModel):
    success: bool
    extracted_content: str = ""
    error: str | None = None

    @classmethod
    def ok(cls, extracted_content: str = "") -> Self:
        return cls(success=True, extracted_content=extracted_content)

    @classmethod
    def fail(cls, error: Exception | str) -> Self:
        return cls(success=False, extracted_content="", error=str(error))


class Tool:
    def __init__(
        self,
        name: str,
        description: str | None,
        fn: Callable[..., Any],
        status_label: Callable[[Any], str] | None = None,
        action_type: ActionType = ActionType.FETCH,
        schema: dict | None = None,
        param_model: type[BaseModel] | None = None,
        suspends_for_input: bool = False,
    ) -> None:
        self.name = name
        self.description = description
        self.fn = fn
        self.action_type = action_type
        self._schema = schema
        self.param_model = param_model
        self.suspends_for_input = suspends_for_input
        self._status_label = status_label
        self._schema_builder = (
            None if schema else ToolSchemaBuilder(self.fn, param_model)
        )

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


class SearchParams(ToolParams):
    query: str
    limit: int = 10


class ArtistAlbumsParams(ToolParams):
    artist_id: str = Field(description="URI or ID.")
    include_groups: str = Field(default="album,single", description="Comma-separated.")
    limit: int = 20


class ArtistTopTracksParams(ToolParams):
    artist_id: str = Field(description="URI or ID.")
    country: str = Field(default="DE", description="ISO 3166-1 alpha-2.")


class AlbumTracksParams(ToolParams):
    album_id: str = Field(description="URI or ID.")


class CreateDraftPlaylistParams(ToolParams):
    name: str


class AddDraftPlaylistTracksParams(ToolParams):
    tracks: list[TrackRef] = Field(min_length=1)


class RemoveDraftPlaylistTracksParams(ToolParams):
    track_ids: list[UUID] = Field(min_length=1)


class ReplaceDraftPlaylistTracksParams(ToolParams):
    replacements: list[TrackRefReplacement] = Field(min_length=1)


class PlaylistIdParams(ToolParams):
    playlist_id: str


class GenerateCardsParams(ToolParams):
    playlist_id: str


class AskFollowUpOption(BaseModel):
    label: str


class AskFollowUpQuestion(BaseModel):
    question: str
    options: list[AskFollowUpOption] = Field(min_length=1, max_length=4)


class AskFollowUpParams(ToolParams):
    questions: list[AskFollowUpQuestion] = Field(min_length=1, max_length=4)
