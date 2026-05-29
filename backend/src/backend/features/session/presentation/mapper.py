from backend.features.session.application import ExportedSpotifyPlaylist
from backend.features.session.application.ports.session_summary_query import (
    SessionSummary,
)
from backend.features.session.domain import (
    ArtistReference,
    AssistantMessage,
    CompletedCall,
    FailedCall,
    FollowUpQuestion,
    FollowUpQuestionGroup,
    PendingCall,
    Playlist,
    PlaylistReference,
    PlaylistTrack,
    Session,
    SessionEntry,
    ToolCall,
    ToolCallSequence,
    UserMessage,
    UserMessageAttachment,
    UserCurationEvent,
)
from backend.features.session.presentation.schemas import (
    ArtistReferenceResponse,
    AssistantMessageEntryResponse,
    FollowUpOptionResponse,
    FollowUpQuestionGroupEntryResponse,
    FollowUpQuestionResponse,
    PlaylistResponse,
    PlaylistReferenceResponse,
    PlaylistTrackResponse,
    SessionEntryResponse,
    SessionResponse,
    SessionSummaryResponse,
    SpotifyPlaylistExportResponse,
    ToolCallSequenceEntryResponse,
    ToolCallResponse,
    ToolCallState,
    ToolFunctionResponse,
    SessionMessageAttachmentResponse,
    UserCurationEventResponse,
    UserMessageEntryResponse,
)


def to_session_response(session: Session) -> SessionResponse:
    return SessionResponse(
        id=session.id,
        title=session.title,
        is_starred=session.is_starred,
        phase=session.phase,
        created_at=session.created_at,
        entries=[to_entry_response(entry) for entry in session.entries],
        playlist=to_playlist_response(session.playlist),
        playlist_references=[
            to_playlist_reference_response(reference)
            for reference in session.playlist_references
        ],
        artist_references=[
            to_artist_reference_response(reference)
            for reference in session.artist_references
        ],
        unconsumed_user_curation_events=[
            to_user_curation_event_response(event)
            for event in session.unconsumed_user_curation_events
        ],
    )


def to_entry_response(entry: SessionEntry) -> SessionEntryResponse:
    if isinstance(entry, UserMessage):
        return UserMessageEntryResponse(
            id=entry.id,
            content=entry.content,
            attachments=[
                to_user_message_attachment_response(attachment)
                for attachment in entry.attachments
            ],
            user_curation_events=[
                to_user_curation_event_response(event)
                for event in entry.user_curation_events
            ],
            created_at=entry.created_at,
        )
    if isinstance(entry, AssistantMessage):
        return AssistantMessageEntryResponse(
            id=entry.id,
            content=entry.content,
            created_at=entry.created_at,
        )
    if isinstance(entry, ToolCallSequence):
        return to_tool_call_sequence_response(entry)
    if isinstance(entry, FollowUpQuestionGroup):
        return to_follow_up_group_response(entry)
    raise TypeError(f"Unsupported session entry: {type(entry).__name__}")


def to_tool_call_sequence_response(
    sequence: ToolCallSequence,
) -> ToolCallSequenceEntryResponse:
    return ToolCallSequenceEntryResponse(
        id=sequence.id,
        created_at=sequence.created_at,
        calls=[to_tool_call_response(call) for call in sequence.calls],
    )


def to_tool_call_response(call: ToolCall) -> ToolCallResponse:
    if isinstance(call, CompletedCall):
        state, result, error = ToolCallState.COMPLETED, call.result, None
    elif isinstance(call, FailedCall):
        state, result, error = ToolCallState.FAILED, None, call.error
    elif isinstance(call, PendingCall):
        state, result, error = ToolCallState.PENDING, None, None
    else:
        raise TypeError(f"Unsupported tool call: {type(call).__name__}")
    return ToolCallResponse(
        id=call.id,
        function=ToolFunctionResponse(
            name=call.function.name,
            arguments=call.function.arguments,
            status_label=call.function.status_label,
            action_type=(
                call.function.action_type.value
                if call.function.action_type is not None
                else None
            ),
        ),
        state=state,
        result=result,
        error=error,
    )


def to_follow_up_group_response(
    group: FollowUpQuestionGroup,
) -> FollowUpQuestionGroupEntryResponse:
    return FollowUpQuestionGroupEntryResponse(
        id=group.id,
        created_at=group.created_at,
        questions=[to_follow_up_question_response(q) for q in group.questions],
    )


def to_follow_up_question_response(
    question: FollowUpQuestion,
) -> FollowUpQuestionResponse:
    return FollowUpQuestionResponse(
        id=question.id,
        question=question.question,
        options=[
            FollowUpOptionResponse(id=option.id, label=option.label)
            for option in question.options
        ],
        state=question.state.value,
        answer_text=question.answer_text,
        answered_option_id=question.answered_option_id,
    )


def to_session_summary_response(session: SessionSummary) -> SessionSummaryResponse:
    return SessionSummaryResponse(
        id=session.id,
        title=session.title,
        is_starred=session.is_starred,
        created_at=session.created_at,
        last_activity_at=session.last_activity_at,
    )


def to_playlist_track_response(track: PlaylistTrack) -> PlaylistTrackResponse:
    return PlaylistTrackResponse(
        id=track.id,
        title=track.title,
        artist=track.artist,
        year=track.year,
        spotify_uri=track.spotify_uri,
        cover_url=track.cover_url,
        is_pinned=track.is_pinned,
    )


def to_spotify_playlist_export_response(
    exported: ExportedSpotifyPlaylist,
) -> SpotifyPlaylistExportResponse:
    return SpotifyPlaylistExportResponse(
        id=exported.id,
        name=exported.name,
        description=exported.description,
        url=exported.url,
        track_count=exported.track_count,
    )


def to_playlist_response(playlist: Playlist | None) -> PlaylistResponse | None:
    if playlist is None:
        return None
    return PlaylistResponse(
        id=playlist.id,
        name=playlist.name,
        tracks=[to_playlist_track_response(track) for track in playlist.tracks],
    )


def to_playlist_reference_response(
    reference: PlaylistReference,
) -> PlaylistReferenceResponse:
    return PlaylistReferenceResponse(
        id=reference.id,
        spotify_playlist_id=reference.spotify_playlist_id,
        name=reference.name,
        owner=reference.owner,
        cover_url=reference.cover_url,
        total_tracks=reference.total_tracks,
    )


def to_artist_reference_response(reference: ArtistReference) -> ArtistReferenceResponse:
    return ArtistReferenceResponse(
        id=reference.id,
        spotify_artist_id=reference.spotify_artist_id,
        name=reference.name,
        image_url=reference.image_url,
        genres=list(reference.genres),
        followers=reference.followers,
        popularity=reference.popularity,
    )


def to_user_message_attachment_response(
    attachment: UserMessageAttachment,
) -> SessionMessageAttachmentResponse:
    return SessionMessageAttachmentResponse(
        kind=attachment.kind.value,
        external_id=attachment.external_id,
        title=attachment.title,
        subtitle=attachment.subtitle,
        image_url=attachment.image_url,
        spotify_id=attachment.spotify_id,
    )


def to_user_curation_event_response(
    event: UserCurationEvent,
) -> UserCurationEventResponse:
    return UserCurationEventResponse(
        id=event.id,
        event_type=event.event_type.value,
        track_id=event.track_id,
        track_title=event.track_title,
        track_artist=event.track_artist,
        track_year=event.track_year,
        track_spotify_uri=event.track_spotify_uri,
        track_cover_url=event.track_cover_url,
        occurred_at=event.occurred_at,
    )
