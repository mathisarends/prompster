import json
from collections.abc import AsyncIterator

from agent.agent import (
    Agent,
    AssistantMessageChunkEvent,
    AssistantMessageEvent,
    FollowUpRequestedEvent,
    ToolCallEvent,
    ToolResultEvent,
    WorkspaceUpdatedEvent,
)
from agent import MessageManager, Spotify
from agent.tools.views import AskFollowUpQuestion
from agent.workspace import (
    PlaylistDraft,
    PlaylistDraftTrack,
    PlaylistDraftTracksAdded,
    PlaylistDraftTracksRemoved,
    PlaylistDraftTracksReplaced,
    WorkspaceStore,
)

from llmify import ChatModel
from llmify.messages import ToolCall as LLMToolCall
from spotifyify import Spotifyify

from backend.features.session.application.ports.session_runner import (
    SessionRunner,
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
    AssistantMessage,
    CompletedCall,
    FailedCall,
    FollowUpOption,
    FollowUpQuestion,
    PendingCall,
    Playlist,
    PlaylistTrack,
    Session,
    ToolCall,
    ToolCallSequence,
    ToolFunction,
    UserMessage,
)


class AgentSessionRunner(SessionRunner):
    def __init__(
        self,
        llm: ChatModel,
        spotify: Spotifyify,
        system_prompt: str | None = None,
    ) -> None:
        self._llm = llm
        self._spotify = spotify
        self._system_prompt = system_prompt

    async def run(self, *, session: Session) -> AsyncIterator[SessionRunnerEvent]:
        agent = Agent(
            llm=self._llm,
            messages=_to_message_manager(
                session=session,
                system_prompt=self._system_prompt,
            ),
            spotify=Spotify(client=self._spotify),
            workspace_store=_to_workspace_store(session.playlist),
        )

        try:
            async for event in agent.continue_stream():
                if isinstance(event, AssistantMessageChunkEvent):
                    yield SessionRunnerAssistantMessageChunk(chunk=event.chunk)
                elif isinstance(event, AssistantMessageEvent):
                    yield SessionRunnerAssistantMessage(content=event.content)
                elif isinstance(event, ToolCallEvent):
                    yield SessionRunnerToolCallStarted(
                        call=PendingCall(
                            id=event.tool_call_id,
                            function=ToolFunction(
                                name=event.name,
                                arguments=dict(event.args),
                                status_label=event.status_label,
                            ),
                        )
                    )
                elif isinstance(event, ToolResultEvent):
                    yield SessionRunnerToolCallCompleted(
                        tool_call_id=event.tool_call_id,
                        result=event.result,
                    )
                elif isinstance(event, FollowUpRequestedEvent):
                    yield SessionRunnerFollowUpRequested(
                        questions=[
                            _to_follow_up_question(question)
                            for question in event.questions
                        ]
                    )
                elif isinstance(event, WorkspaceUpdatedEvent):
                    update = event.update
                    if isinstance(update, PlaylistDraftTracksAdded):
                        yield SessionRunnerPlaylistTracksAdded(
                            playlist_id=update.playlist_draft.id,
                            tracks=[
                                _to_playlist_track(track) for track in update.tracks
                            ],
                        )
                    elif isinstance(update, PlaylistDraftTracksRemoved):
                        yield SessionRunnerPlaylistTracksRemoved(
                            playlist_id=update.playlist_draft.id,
                            track_ids=update.track_ids,
                        )
                    elif isinstance(update, PlaylistDraftTracksReplaced):
                        yield SessionRunnerPlaylistTracksReplaced(
                            playlist_id=update.playlist_draft.id,
                            replacements=[
                                SessionRunnerPlaylistTrackReplacement(
                                    track_id=replacement.track_id,
                                    track=_to_playlist_track(replacement.track),
                                )
                                for replacement in update.replacements
                            ],
                        )
                    else:
                        yield SessionRunnerPlaylistUpdated(
                            playlist=_to_playlist(event.playlist_draft)
                        )
        finally:
            await agent.close()


def _to_message_manager(
    *,
    session: Session,
    system_prompt: str | None,
) -> MessageManager:
    manager = MessageManager(system_prompt=system_prompt)
    for entry in session.entries:
        if isinstance(entry, UserMessage):
            manager.add_user(entry.content)
        elif isinstance(entry, AssistantMessage):
            manager.add_assistant(entry.content)
        elif isinstance(entry, ToolCallSequence):
            for call in entry.calls:
                manager.add_assistant("", tool_calls=[_to_llm_tool_call(call)])
                if isinstance(call, CompletedCall):
                    manager.add_tool_result(
                        tool_call_id=call.id,
                        content=call.result,
                    )
                elif isinstance(call, FailedCall):
                    manager.add_tool_result(
                        tool_call_id=call.id,
                        content=call.error,
                    )
    playlist_context = _to_playlist_context(session.playlist)
    if playlist_context is not None:
        manager.add_user(playlist_context)
    return manager


def _to_llm_tool_call(call: ToolCall) -> LLMToolCall:
    return LLMToolCall(
        id=call.id,
        function={
            "name": call.function.name,
            "arguments": json.dumps(
                call.function.arguments,
                ensure_ascii=False,
            ),
        },
    )


def _to_follow_up_question(question: AskFollowUpQuestion) -> FollowUpQuestion:
    return FollowUpQuestion(
        question=question.question,
        options=[
            FollowUpOption(id=str(index + 1), label=option.label)
            for index, option in enumerate(question.options)
        ],
    )


def _to_playlist(playlist_draft: PlaylistDraft) -> Playlist:
    return Playlist(
        id=playlist_draft.id,
        name=playlist_draft.name,
        tracks=[_to_playlist_track(track) for track in playlist_draft.tracks],
    )


def _to_playlist_track(track: PlaylistDraftTrack) -> PlaylistTrack:
    return PlaylistTrack(
        id=track.id,
        title=track.title,
        artist=track.artist,
        year=track.year,
        spotify_uri=track.spotify_uri,
        cover_url=track.cover_url,
        is_pinned=track.is_pinned,
    )


def _to_workspace_store(playlist: Playlist | None) -> WorkspaceStore:
    if playlist is None:
        return WorkspaceStore()

    return WorkspaceStore(
        PlaylistDraft(
            id=playlist.id,
            name=playlist.name or "Playlist",
            tracks=[
                PlaylistDraftTrack(
                    id=track.id,
                    title=track.title,
                    artist=track.artist,
                    year=track.year,
                    spotify_uri=track.spotify_uri,
                    cover_url=track.cover_url,
                    is_pinned=track.is_pinned,
                )
                for track in playlist.tracks
            ],
        )
    )


def _to_playlist_context(playlist: Playlist | None) -> str | None:
    if playlist is None:
        return None

    tracks = [
        {
            "id": str(track.id),
            "title": track.title,
            "artist": track.artist,
            "year": track.year,
            "spotify_uri": track.spotify_uri,
            "cover_url": track.cover_url,
            "is_pinned": track.is_pinned,
        }
        for track in playlist.tracks
    ]
    return json.dumps(
        {
            "current_playlist_context": {
                "id": str(playlist.id),
                "name": playlist.name,
                "pinned_tracks_are_hard_constraints": True,
                "tracks": tracks,
            }
        },
        ensure_ascii=False,
    )
