from collections.abc import AsyncIterator
from uuid import UUID

from fastapi_canon import APIRouter, Inject, ServiceScope

from backend.features.session.application import (
    SessionConversationService,
    SessionSpotifyPlaylistExporter,
)
from backend.features.session.presentation.mapper import (
    to_session_image_attachment_references,
    to_session_message_attachments,
)
from backend.features.session.presentation.schemas import (
    CompleteOnboardingRequest,
    SendMessageRequest,
)
from backend.features.session.presentation.streams.events import SessionStreamEvent
from backend.features.session.presentation.streams.spotify_export import (
    SpotifyExportEvent,
    spotify_export_events,
)
from backend.features.session.presentation.streams.stream import session_events
from backend.presentation import AUTHENTICATION_REQUIRED_ERROR, AuthenticatedUserId

stream_router = APIRouter(
    prefix="/sessions",
    tags=["session-streams"],
    raises=(AUTHENTICATION_REQUIRED_ERROR,),
)


@stream_router.sse("/{session_id}/messages", methods=["POST"])
async def send_message(
    session_id: UUID,
    body: SendMessageRequest,
    authenticated_user_id: AuthenticatedUserId,
    conversations: Inject[ServiceScope[SessionConversationService]],
) -> AsyncIterator[SessionStreamEvent]:
    """Send a message and stream the resulting session updates."""
    attachments = to_session_message_attachments(body.attachments)
    images = to_session_image_attachment_references(body.image_attachments)
    async with conversations() as service:
        events = service.send_message(
            session_id=session_id,
            user_id=authenticated_user_id,
            content=body.content,
            model_id=body.model_id,
            attachments=attachments,
            image_attachments=images,
        )
        async for event in session_events(events):
            yield event


@stream_router.sse("/{session_id}/onboarding/complete", methods=["POST"])
async def complete_onboarding(
    session_id: UUID,
    body: CompleteOnboardingRequest,
    authenticated_user_id: AuthenticatedUserId,
    conversations: Inject[ServiceScope[SessionConversationService]],
) -> AsyncIterator[SessionStreamEvent]:
    """Complete onboarding and stream the resulting session updates."""
    async with conversations() as service:
        events = service.complete_onboarding(
            session_id=session_id,
            user_id=authenticated_user_id,
            model_id=body.model_id,
        )
        async for event in session_events(events):
            yield event


@stream_router.sse("/{session_id}/playlist/spotify-export", methods=["POST"])
async def export_spotify(
    session_id: UUID,
    authenticated_user_id: AuthenticatedUserId,
    exporters: Inject[ServiceScope[SessionSpotifyPlaylistExporter]],
) -> AsyncIterator[SpotifyExportEvent]:
    """Export the session playlist with retry updates and the final playlist."""
    async with exporters() as exporter:
        events = spotify_export_events(
            exporter, session_id=session_id, user_id=authenticated_user_id
        )
        async for event in events:
            yield event
