from collections.abc import AsyncGenerator
from contextlib import aclosing

from backend.features.session.application import (
    SessionConversationService,
    SessionSpotifyPlaylistExporter,
)
from backend.features.session.presentation.mapper import (
    to_session_image_attachment_references,
    to_session_message_attachments,
)
from rpckit import Inject, RpcChannel

from .context import SessionRpcContext
from .events import ServerEvent
from .params import CompleteOnboardingParams, SendMessageParams
from .spotify_export import SpotifyExportServerEvent, spotify_export_events
from .stream import session_events

session_channel = RpcChannel("session")


@session_channel.method()
async def ping() -> str:
    """Check that the session connection is available."""
    return "pong"


@session_channel.subscription()
async def send_message(
    params: SendMessageParams,
    context: Inject[SessionRpcContext],
    service: Inject[SessionConversationService],
) -> AsyncGenerator[ServerEvent]:
    """Send a message and stream the resulting session updates."""
    async with aclosing(
        session_events(
            service.send_message(
                session_id=context.session_id,
                user_id=context.user_id,
                content=params.content,
                model_id=params.model_id,
                attachments=to_session_message_attachments(params.attachments),
                image_attachments=to_session_image_attachment_references(
                    params.image_attachments
                ),
            )
        )
    ) as events:
        async for event in events:
            yield event


@session_channel.subscription()
async def complete_onboarding(
    params: CompleteOnboardingParams,
    context: Inject[SessionRpcContext],
    service: Inject[SessionConversationService],
) -> AsyncGenerator[ServerEvent]:
    """Complete onboarding and stream the resulting session updates."""
    async with aclosing(
        session_events(
            service.complete_onboarding(
                session_id=context.session_id,
                user_id=context.user_id,
                model_id=params.model_id,
            )
        )
    ) as events:
        async for event in events:
            yield event


@session_channel.subscription()
async def export_spotify(
    context: Inject[SessionRpcContext],
    exporter: Inject[SessionSpotifyPlaylistExporter],
) -> AsyncGenerator[SpotifyExportServerEvent]:
    """Export the session playlist with retry updates and the final playlist."""
    async with aclosing(
        spotify_export_events(
            exporter, session_id=context.session_id, user_id=context.user_id
        )
    ) as events:
        async for event in events:
            yield event
