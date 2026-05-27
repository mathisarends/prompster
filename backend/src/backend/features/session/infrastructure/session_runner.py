import json
from collections.abc import AsyncIterator
from uuid import UUID

from agent.agent import (
    Agent,
    AssistantMessageChunkEvent,
    AssistantMessageEvent,
    FollowUpRequestedEvent,
    ToolCallEvent,
    ToolResultEvent,
    WorkspaceUpdatedEvent,
)
from agent import Spotify, UserEvent
from agent.tools.views import AskFollowUpQuestion
from agent.playlist import (
    PlaylistDraft,
    PlaylistDraftTrack,
    PlaylistDraftTracksAdded,
    PlaylistDraftTracksRemoved,
    PlaylistDraftTracksReplaced,
    PlaylistDraftStore,
)

from llmify import ChatModel
from llmify.messages import (
    AssistantMessage as LLMAssistantMessage,
    Message as LLMMessage,
    ToolCall as LLMToolCall,
    ToolResultMessage as LLMToolResultMessage,
    UserMessage as LLMUserMessage,
)
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
    ToolActionType,
    ToolCall,
    ToolCallSequence,
    ToolFunction,
    UserCurationEvent,
    UserMessage,
    UserMessageAttachment,
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
            history=_to_history_messages(
                session=session,
            ),
            user_events=_to_user_events(session=session),
            system_prompt=self._system_prompt,
            spotify=Spotify(client=self._spotify),
            playlist_store=_to_playlist_draft_store(session.playlist),
        )

        try:
            async for event in agent.stream():
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
                                action_type=_to_tool_action_type(event.action_type),
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


def _to_history_messages(
    *,
    session: Session,
) -> list[LLMMessage]:
    messages: list[LLMMessage] = []
    for entry in session.entries:
        if isinstance(entry, UserMessage):
            messages.append(LLMUserMessage(content=_to_user_message_content(entry)))
        elif isinstance(entry, AssistantMessage):
            messages.append(LLMAssistantMessage(content=entry.content))
        elif isinstance(entry, ToolCallSequence):
            for call in entry.calls:
                messages.append(
                    LLMAssistantMessage(
                        content="", tool_calls=[_to_llm_tool_call(call)]
                    )
                )
                if isinstance(call, CompletedCall):
                    messages.append(
                        LLMToolResultMessage(
                            tool_call_id=call.id,
                            content=call.result,
                        )
                    )
                elif isinstance(call, FailedCall):
                    messages.append(
                        LLMToolResultMessage(
                            tool_call_id=call.id,
                            content=call.error,
                        )
                    )
    return messages


def _to_tool_action_type(value: str | None) -> ToolActionType | None:
    if value is None:
        return None
    try:
        return ToolActionType(value)
    except ValueError:
        return None


def _to_user_message_content(message: UserMessage) -> str:
    if not message.attachments:
        return message.content

    payload = {
        "attachment_references": [
            _to_attachment_payload(attachment) for attachment in message.attachments
        ]
    }
    attachment_context = json.dumps(payload, ensure_ascii=False)
    if message.content.strip():
        return f"{message.content}\n\n{attachment_context}"
    return attachment_context


def _to_attachment_payload(attachment: UserMessageAttachment) -> dict[str, str | None]:
    return {
        "kind": attachment.kind.value,
        "external_id": attachment.external_id,
        "title": attachment.title,
        "subtitle": attachment.subtitle,
        "image_url": attachment.image_url,
        "spotify_id": attachment.spotify_id,
    }


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


def _to_playlist_draft_store(playlist: Playlist | None) -> PlaylistDraftStore:
    if playlist is None:
        return PlaylistDraftStore()

    return PlaylistDraftStore(
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


def _to_user_events(*, session: Session) -> list[UserEvent]:
    user_events: list[UserEvent] = []
    bound_event_ids: set[UUID] = set()
    history_index = 0

    for entry in session.entries:
        if isinstance(entry, UserMessage):
            for event in entry.user_curation_events:
                if event.consumed:
                    continue
                user_events.append(
                    _to_user_event(event=event, history_index=history_index)
                )
                bound_event_ids.add(event.id)
            history_index += 1
            continue

        if isinstance(entry, AssistantMessage) and entry.content.strip():
            history_index += 1

    for event in session.unconsumed_user_curation_events:
        if event.id in bound_event_ids:
            continue
        user_events.append(_to_user_event(event=event, history_index=history_index))

    return user_events


def _to_user_event(*, event: UserCurationEvent, history_index: int) -> UserEvent:
    return UserEvent(
        type=event.event_type.value,
        track_title=event.track_title,
        track_artist=event.track_artist,
        occurred_at=event.occurred_at,
        history_index=history_index,
    )
