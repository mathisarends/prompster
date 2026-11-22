from uuid import UUID

from backend.features.auth.presentation.dependencies import AuthenticatedUserId
from backend.features.auth.presentation.exceptions import (
    AUTHENTICATION_REQUIRED_ERROR,
)
from backend.features.session.application import (
    SessionConversationService,
    SessionImageUrlResolver,
    SessionPlaylistExporter,
    SessionService,
)
from backend.features.session.presentation.exceptions import (
    INVALID_SESSION_PHASE_TRANSITION_ERROR,
    INVALID_SPOTIFY_TRACK_URI_ERROR,
    PLAYLIST_TRACK_LIMIT_EXCEEDED_ERROR,
    PLAYLIST_TRACK_NOT_FOUND_ERROR,
    SESSION_ACCESS_DENIED_ERROR,
    SESSION_NOT_FOUND_ERROR,
    SESSION_PLAYLIST_EMPTY_ERROR,
    SPOTIFY_TRACK_NOT_FOUND_ERROR,
    SPOTIFY_TRACK_YEAR_MISSING_ERROR,
    USER_CURATION_EVENT_ALREADY_CONSUMED_ERROR,
    USER_CURATION_EVENT_MISSING_TRACK_YEAR_ERROR,
    USER_CURATION_EVENT_NOT_FOUND_ERROR,
)
from backend.features.session.presentation.mapper import (
    to_playlist_track_response,
    to_session_response,
    to_session_summary_list_response,
)
from backend.features.session.presentation.schemas import (
    AddPlaylistTrackRequest,
    AddSpotifyPlaylistTrackRequest,
    PlaylistTrackResponse,
    SessionResponse,
    SessionSummaryListResponse,
    SessionUpdateRequest,
    SubmitOnboardingAnswerRequest,
)
from backend.features.spotify.application import SpotifySearch
from fastapi import Query, Response, status
from fastapi_canon import APIRouter, CanonResponse, Inject

router = APIRouter(
    prefix="/sessions",
    tags=["sessions"],
    raises=(AUTHENTICATION_REQUIRED_ERROR,),
)


@router.get(
    "",
    response_model=SessionSummaryListResponse,
    status_code=status.HTTP_200_OK,
    operation_id="list_sessions",
)
async def list_sessions(
    authenticated_user_id: AuthenticatedUserId,
    service: Inject[SessionService],
    q: str | None = Query(default=None, min_length=1, max_length=120),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> SessionSummaryListResponse:
    items = await service.list(
        owner_id=authenticated_user_id,
        query=q,
        limit=limit,
        offset=offset,
    )

    return to_session_summary_list_response(items)


@router.get(
    "/{session_id}",
    response_model=SessionResponse,
    status_code=status.HTTP_200_OK,
    operation_id="get_session",
    raises=(
        SESSION_NOT_FOUND_ERROR,
        SESSION_ACCESS_DENIED_ERROR,
    ),
)
async def get_session_by_id(
    session_id: UUID,
    authenticated_user_id: AuthenticatedUserId,
    service: Inject[SessionService],
    image_url_resolver: Inject[SessionImageUrlResolver],
) -> SessionResponse:
    session = await service.get_by_id(
        session_id=session_id,
        user_id=authenticated_user_id,
    )
    image_urls_by_storage_key = await image_url_resolver.resolve(session=session)
    return to_session_response(
        session,
        image_urls_by_storage_key=image_urls_by_storage_key,
    )


@router.post(
    "",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="create_session",
)
async def create_session(
    authenticated_user_id: AuthenticatedUserId,
    service: Inject[SessionService],
    image_url_resolver: Inject[SessionImageUrlResolver],
) -> SessionResponse:
    session = await service.create(
        owner_id=authenticated_user_id,
    )
    image_urls_by_storage_key = await image_url_resolver.resolve(session=session)
    return to_session_response(
        session,
        image_urls_by_storage_key=image_urls_by_storage_key,
    )


@router.post(
    "/{session_id}/onboarding-answer",
    response_model=SessionResponse,
    status_code=status.HTTP_200_OK,
    operation_id="submit_onboarding_answer",
    raises=(
        SESSION_NOT_FOUND_ERROR,
        SESSION_ACCESS_DENIED_ERROR,
        INVALID_SESSION_PHASE_TRANSITION_ERROR,
    ),
)
async def submit_onboarding_answer(
    session_id: UUID,
    authenticated_user_id: AuthenticatedUserId,
    body: SubmitOnboardingAnswerRequest,
    service: Inject[SessionConversationService],
    image_url_resolver: Inject[SessionImageUrlResolver],
) -> SessionResponse:
    session = await service.submit_onboarding_answer(
        session_id=session_id,
        user_id=authenticated_user_id,
        question_id=body.question_id,
        answer=body.answer,
        answers=body.answers,
    )
    image_urls_by_storage_key = await image_url_resolver.resolve(session=session)
    return to_session_response(
        session,
        image_urls_by_storage_key=image_urls_by_storage_key,
    )


@router.post(
    "/{session_id}/messages/stop",
    operation_id="stop_message",
    raises=(
        SESSION_NOT_FOUND_ERROR,
        SESSION_ACCESS_DENIED_ERROR,
    ),
    response=CanonResponse.empty(),
)
async def stop_message(
    session_id: UUID,
    authenticated_user_id: AuthenticatedUserId,
    service: Inject[SessionConversationService],
) -> Response:
    await service.stop_message(
        session_id=session_id,
        user_id=authenticated_user_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{session_id}/tracks",
    response_model=PlaylistTrackResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="add_playlist_track",
    raises=(
        SESSION_NOT_FOUND_ERROR,
        SESSION_ACCESS_DENIED_ERROR,
        PLAYLIST_TRACK_LIMIT_EXCEEDED_ERROR,
    ),
)
async def add_session_playlist_track(
    session_id: UUID,
    authenticated_user_id: AuthenticatedUserId,
    body: AddPlaylistTrackRequest,
    service: Inject[SessionService],
) -> PlaylistTrackResponse:
    track = await service.add_track(
        session_id=session_id,
        user_id=authenticated_user_id,
        title=body.title,
        artist=body.artist,
        year=body.year,
        spotify_uri=body.spotify_uri,
        cover_url=body.cover_url,
    )
    return to_playlist_track_response(track)


@router.post(
    "/{session_id}/tracks/spotify",
    response_model=PlaylistTrackResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="add_spotify_playlist_track",
    raises=(
        SESSION_NOT_FOUND_ERROR,
        SESSION_ACCESS_DENIED_ERROR,
        PLAYLIST_TRACK_LIMIT_EXCEEDED_ERROR,
        INVALID_SPOTIFY_TRACK_URI_ERROR,
        SPOTIFY_TRACK_NOT_FOUND_ERROR,
        SPOTIFY_TRACK_YEAR_MISSING_ERROR,
    ),
)
async def add_session_spotify_playlist_track(
    session_id: UUID,
    authenticated_user_id: AuthenticatedUserId,
    body: AddSpotifyPlaylistTrackRequest,
    service: Inject[SessionService],
    spotify_search: Inject[SpotifySearch],
) -> PlaylistTrackResponse:
    spotify_track = await spotify_search.get_track(spotify_uri=body.spotify_uri)
    assert spotify_track.year is not None

    track = await service.add_track(
        session_id=session_id,
        user_id=authenticated_user_id,
        title=spotify_track.title,
        artist=spotify_track.artist,
        year=spotify_track.year,
        spotify_uri=f"spotify:track:{spotify_track.id}",
        cover_url=spotify_track.cover_url,
    )
    return to_playlist_track_response(track)


@router.delete(
    "/{session_id}/tracks/{track_id}",
    operation_id="remove_playlist_track",
    raises=(
        SESSION_NOT_FOUND_ERROR,
        SESSION_ACCESS_DENIED_ERROR,
        PLAYLIST_TRACK_NOT_FOUND_ERROR,
    ),
    response=CanonResponse.empty(),
)
async def remove_session_playlist_track(
    session_id: UUID,
    track_id: UUID,
    authenticated_user_id: AuthenticatedUserId,
    service: Inject[SessionService],
) -> Response:
    await service.remove_track(
        session_id=session_id,
        user_id=authenticated_user_id,
        track_id=track_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{session_id}/curation-events/{event_id}/restore",
    response_model=SessionResponse,
    status_code=status.HTTP_200_OK,
    operation_id="restore_user_curation_event",
    raises=(
        SESSION_NOT_FOUND_ERROR,
        SESSION_ACCESS_DENIED_ERROR,
        USER_CURATION_EVENT_NOT_FOUND_ERROR,
        USER_CURATION_EVENT_ALREADY_CONSUMED_ERROR,
        USER_CURATION_EVENT_MISSING_TRACK_YEAR_ERROR,
    ),
)
async def restore_session_user_curation_event(
    session_id: UUID,
    event_id: UUID,
    authenticated_user_id: AuthenticatedUserId,
    service: Inject[SessionService],
    image_url_resolver: Inject[SessionImageUrlResolver],
) -> SessionResponse:
    session = await service.restore_user_curation_event(
        session_id=session_id,
        user_id=authenticated_user_id,
        event_id=event_id,
    )
    image_urls_by_storage_key = await image_url_resolver.resolve(session=session)
    return to_session_response(
        session,
        image_urls_by_storage_key=image_urls_by_storage_key,
    )


@router.get(
    "/{session_id}/playlist/pdf",
    operation_id="export_session_playlist",
    raises=(
        SESSION_NOT_FOUND_ERROR,
        SESSION_ACCESS_DENIED_ERROR,
        SESSION_PLAYLIST_EMPTY_ERROR,
    ),
    response=CanonResponse.binary(
        "application/pdf",
        description="Playlist deck PDF.",
        headers=("Content-Disposition",),
    ),
)
async def export_session_playlist(
    session_id: UUID,
    authenticated_user_id: AuthenticatedUserId,
    exporter: Inject[SessionPlaylistExporter],
    pages: int | None = Query(default=None, ge=1, le=100),
) -> Response:
    pdf = await exporter.export(
        session_id=session_id,
        user_id=authenticated_user_id,
        page_limit=pages,
    )
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="session-{session_id}.pdf"'
        },
    )


@router.patch(
    "/{session_id}",
    response_model=SessionResponse,
    status_code=status.HTTP_200_OK,
    operation_id="update_session",
    raises=(
        SESSION_NOT_FOUND_ERROR,
        SESSION_ACCESS_DENIED_ERROR,
    ),
)
async def update_session(
    session_id: UUID,
    authenticated_user_id: AuthenticatedUserId,
    body: SessionUpdateRequest,
    service: Inject[SessionService],
    image_url_resolver: Inject[SessionImageUrlResolver],
) -> SessionResponse:
    session = await service.update(
        session_id=session_id,
        user_id=authenticated_user_id,
        title=body.title,
    )
    image_urls_by_storage_key = await image_url_resolver.resolve(session=session)
    return to_session_response(
        session,
        image_urls_by_storage_key=image_urls_by_storage_key,
    )


@router.post(
    "/{session_id}/star",
    response_model=SessionResponse,
    status_code=status.HTTP_200_OK,
    operation_id="star_session",
    raises=(
        SESSION_NOT_FOUND_ERROR,
        SESSION_ACCESS_DENIED_ERROR,
    ),
)
async def star_session(
    session_id: UUID,
    authenticated_user_id: AuthenticatedUserId,
    service: Inject[SessionService],
    image_url_resolver: Inject[SessionImageUrlResolver],
) -> SessionResponse:
    session = await service.star(
        session_id=session_id,
        user_id=authenticated_user_id,
    )
    image_urls_by_storage_key = await image_url_resolver.resolve(session=session)
    return to_session_response(
        session,
        image_urls_by_storage_key=image_urls_by_storage_key,
    )


@router.post(
    "/{session_id}/unstar",
    response_model=SessionResponse,
    status_code=status.HTTP_200_OK,
    operation_id="unstar_session",
    raises=(
        SESSION_NOT_FOUND_ERROR,
        SESSION_ACCESS_DENIED_ERROR,
    ),
)
async def unstar_session(
    session_id: UUID,
    authenticated_user_id: AuthenticatedUserId,
    service: Inject[SessionService],
    image_url_resolver: Inject[SessionImageUrlResolver],
) -> SessionResponse:
    session = await service.unstar(
        session_id=session_id,
        user_id=authenticated_user_id,
    )
    image_urls_by_storage_key = await image_url_resolver.resolve(session=session)
    return to_session_response(
        session,
        image_urls_by_storage_key=image_urls_by_storage_key,
    )


@router.delete(
    "/{session_id}",
    operation_id="delete_session",
    raises=(
        SESSION_NOT_FOUND_ERROR,
        SESSION_ACCESS_DENIED_ERROR,
    ),
    response=CanonResponse.empty(),
)
async def delete_session(
    session_id: UUID,
    authenticated_user_id: AuthenticatedUserId,
    service: Inject[SessionService],
) -> Response:
    await service.delete(session_id=session_id, user_id=authenticated_user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
