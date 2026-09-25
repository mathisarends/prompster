from collections.abc import AsyncIterator
from dataclasses import dataclass
from uuid import UUID

from fastapi import APIRouter
from rpckit import Inject, RpcChannel, RpcModel, RpcService
from rpckit.dishka import Dishka
from rpckit.fastapi import RpcRoutes

from backend.features.auth.presentation.dependencies import AuthenticatedUserId
from backend.features.session.application import (
    SessionConversationService,
    SessionSpotifyPlaylistExporter,
)
from backend.features.session.presentation.mapper import (
    to_session_image_attachment_references,
    to_session_message_attachments,
)
from backend.features.session.presentation.rpc.events import ServerEvent
from backend.features.session.presentation.rpc.spotify_export import (
    SpotifyExportErrorEvent,
    SpotifyExportServerEvent,
    spotify_export_events,
)
from backend.features.session.presentation.rpc.stream import session_events
from backend.features.session.presentation.schemas import SendMessageRequest


@dataclass(frozen=True, slots=True)
class SessionRpcContext:
    session_id: UUID
    user_id: UUID


class SendMessageParams(SendMessageRequest):
    model_id: str | None = None


class CompleteOnboardingParams(RpcModel):
    model_id: str | None = None


session_channel = RpcChannel("session")


@session_channel.server.method()
async def ping() -> str:
    return "pong"


@session_channel.server.subscription()
async def send_message(
    params: SendMessageParams,
    context: Inject[SessionRpcContext],
    service: Inject[SessionConversationService],
) -> AsyncIterator[ServerEvent]:
    async for event in session_events(
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
    ):
        yield event


@session_channel.server.subscription()
async def complete_onboarding(
    params: CompleteOnboardingParams,
    context: Inject[SessionRpcContext],
    service: Inject[SessionConversationService],
) -> AsyncIterator[ServerEvent]:
    async for event in session_events(
        service.complete_onboarding(
            session_id=context.session_id,
            user_id=context.user_id,
            model_id=params.model_id,
        )
    ):
        yield event


@session_channel.server.subscription()
async def export_spotify(
    context: Inject[SessionRpcContext],
    exporter: Inject[SessionSpotifyPlaylistExporter],
) -> AsyncIterator[SpotifyExportServerEvent]:
    try:
        plan = await exporter.prepare(
            session_id=context.session_id, user_id=context.user_id
        )
    except Exception as exc:
        yield SpotifyExportErrorEvent(
            code=type(exc).__name__, message=str(exc) or type(exc).__name__
        )
        return
    async for event in spotify_export_events(exporter, plan):
        yield event


rpc_service = RpcService()
session_endpoint = rpc_service.socket(
    "/api/v1/sessions/{session_id}/stream",
    channels=[session_channel],
    name="session",
    context=SessionRpcContext,
)
contract = rpc_service.contract(
    title="Prompster session streams",
    base_url="ws://localhost:8000",
)

rpc_router = APIRouter(prefix="/api/v1/sessions")


async def session_rpc_context(
    session_id: UUID,
    authenticated_user_id: AuthenticatedUserId,
) -> SessionRpcContext:
    return SessionRpcContext(session_id=session_id, user_id=authenticated_user_id)


RpcRoutes(rpc_router, context=session_rpc_context, resolver=Dishka()).mount(
    session_endpoint
)
