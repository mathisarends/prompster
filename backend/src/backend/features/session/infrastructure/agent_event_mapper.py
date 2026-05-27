from agent.agent import (
    AssistantMessageChunkEvent,
    AssistantMessageEvent,
    FollowUpRequestedEvent,
    ToolCallEvent,
    ToolResultEvent,
    WorkspaceUpdatedEvent,
)
from agent.playlist import (
    PlaylistDraft,
    PlaylistDraftTrack,
    PlaylistDraftTracksAdded,
    PlaylistDraftTracksRemoved,
    PlaylistDraftTracksReplaced,
)
from agent.tools.views import AskFollowUpQuestion

from backend.features.session.application.ports.session_runner import (
    SessionRunnerAssistantMessage,
    SessionRunnerAssistantMessageChunk,
    SessionRunnerEvent,
    SessionRunnerFollowUpRequested,
    SessionRunnerPlaylistTrackReplacement,
    SessionRunnerPlaylistTracksAdded,
    SessionRunnerPlaylistTracksRemoved,
    SessionRunnerPlaylistTracksReplaced,
    SessionRunnerPlaylistUpdated,
    SessionRunnerToolCallCompleted,
    SessionRunnerToolCallStarted,
)
from backend.features.session.domain import (
    FollowUpOption,
    FollowUpQuestion,
    PendingCall,
    Playlist,
    PlaylistTrack,
    ToolActionType,
    ToolFunction,
)


class AgentSessionEventMapper:
    """Translates ``agent`` stream events into ``SessionRunner`` events.

    Stateless: a single instance is safe to share. Returns a list so a single
    agent event can fan out to zero or many runner events — and so unknown
    events can be silently dropped without breaking the runner's loop.
    """

    def map(self, event: object) -> list[SessionRunnerEvent]:
        match event:
            case AssistantMessageChunkEvent():
                return [self._map_assistant_chunk(event)]
            case AssistantMessageEvent():
                return [self._map_assistant_message(event)]
            case ToolCallEvent():
                return [self._map_tool_call_started(event)]
            case ToolResultEvent():
                return [self._map_tool_call_completed(event)]
            case FollowUpRequestedEvent():
                return [self._map_follow_up_requested(event)]
            case WorkspaceUpdatedEvent():
                return [self._map_workspace_updated(event)]
            case _:
                return []

    def _map_assistant_chunk(
        self, event: AssistantMessageChunkEvent
    ) -> SessionRunnerAssistantMessageChunk:
        return SessionRunnerAssistantMessageChunk(chunk=event.chunk)

    def _map_assistant_message(
        self, event: AssistantMessageEvent
    ) -> SessionRunnerAssistantMessage:
        return SessionRunnerAssistantMessage(content=event.content)

    def _map_tool_call_started(
        self, event: ToolCallEvent
    ) -> SessionRunnerToolCallStarted:
        return SessionRunnerToolCallStarted(
            call=PendingCall(
                id=event.tool_call_id,
                function=ToolFunction(
                    name=event.name,
                    arguments=dict(event.args),
                    status_label=event.status_label,
                    action_type=self._to_tool_action_type(event.action_type),
                ),
            )
        )

    def _map_tool_call_completed(
        self, event: ToolResultEvent
    ) -> SessionRunnerToolCallCompleted:
        return SessionRunnerToolCallCompleted(
            tool_call_id=event.tool_call_id,
            result=event.result,
        )

    def _map_follow_up_requested(
        self, event: FollowUpRequestedEvent
    ) -> SessionRunnerFollowUpRequested:
        return SessionRunnerFollowUpRequested(
            questions=[
                self._to_follow_up_question(question) for question in event.questions
            ]
        )

    def _map_workspace_updated(
        self, event: WorkspaceUpdatedEvent
    ) -> SessionRunnerEvent:
        update = event.update
        match update:
            case PlaylistDraftTracksAdded():
                return SessionRunnerPlaylistTracksAdded(
                    playlist_id=update.playlist_draft.id,
                    tracks=[self._to_playlist_track(track) for track in update.tracks],
                )
            case PlaylistDraftTracksRemoved():
                return SessionRunnerPlaylistTracksRemoved(
                    playlist_id=update.playlist_draft.id,
                    track_ids=update.track_ids,
                )
            case PlaylistDraftTracksReplaced():
                return SessionRunnerPlaylistTracksReplaced(
                    playlist_id=update.playlist_draft.id,
                    replacements=[
                        SessionRunnerPlaylistTrackReplacement(
                            track_id=replacement.track_id,
                            track=self._to_playlist_track(replacement.track),
                        )
                        for replacement in update.replacements
                    ],
                )
            case _:
                return SessionRunnerPlaylistUpdated(
                    playlist=self._to_playlist(event.playlist_draft)
                )

    def _to_tool_action_type(self, value: str | None) -> ToolActionType | None:
        if value is None:
            return None
        try:
            return ToolActionType(value)
        except ValueError:
            return None

    def _to_follow_up_question(self, question: AskFollowUpQuestion) -> FollowUpQuestion:
        return FollowUpQuestion(
            question=question.question,
            options=[
                FollowUpOption(id=str(index + 1), label=option.label)
                for index, option in enumerate(question.options)
            ],
        )

    def _to_playlist(self, playlist_draft: PlaylistDraft) -> Playlist:
        return Playlist(
            id=playlist_draft.id,
            name=playlist_draft.name,
            tracks=[self._to_playlist_track(track) for track in playlist_draft.tracks],
        )

    def _to_playlist_track(self, track: PlaylistDraftTrack) -> PlaylistTrack:
        return PlaylistTrack(
            id=track.id,
            title=track.title,
            artist=track.artist,
            year=track.year,
            spotify_uri=track.spotify_uri,
            cover_url=track.cover_url,
            is_pinned=track.is_pinned,
        )
