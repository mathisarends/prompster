import logging
from uuid import UUID

from dishka import AsyncContainer
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from pydantic import TypeAdapter, ValidationError
from starlette.websockets import WebSocketState

from backend.features.auth.application.ports import TokenIssuer
from backend.features.auth.application.schemas import TokenType
from backend.features.auth.infrastructure.auth_settings import AuthSettings
from backend.features.session.domain import (
    EmptyFollowUpAnswerError,
    FollowUpOptionNotFoundError,
    FollowUpQuestionAlreadyResolvedError,
    FollowUpQuestionNotFoundError,
    NoPendingFollowUpGroupError,
    PendingFollowUpQuestionsError,
    PendingToolCallsError,
    PlaylistTrackNotFoundError,
    Session,
    SessionAccessDeniedError,
    SessionNotFoundError,
    SessionRepository,
)
from backend.features.session.presentation.ws_events import (
    AddPlaylistTrackCommand,
    AnswerFollowUpWithOptionCommand,
    AnswerFollowUpWithTextCommand,
    ClientEvent,
    ErrorEvent,
    FollowUpAnsweredEvent,
    FollowUpSkippedEvent,
    PlaylistSetEvent,
    PlaylistTrackAddedEvent,
    PlaylistTrackRemovedEvent,
    RemovePlaylistTrackCommand,
    SendMessageCommand,
    ServerEvent,
    SessionSnapshotEvent,
    SkipFollowUpCommand,
    UserMessageAppendedEvent,
    WebSocketEventCatalog,
)
from backend.features.session.presentation.ws_mapper import (
    to_message_payload,
    to_playlist_payload,
    to_playlist_track_payload,
    to_session_snapshot_payload,
)

logger = logging.getLogger(__name__)

_CLIENT_EVENT_ADAPTER: TypeAdapter[ClientEvent] = TypeAdapter(ClientEvent)
_SERVER_EVENT_ADAPTER: TypeAdapter[ServerEvent] = TypeAdapter(ServerEvent)

ws_router = APIRouter(prefix="/sessions", tags=["sessions-ws"])


@ws_router.get(
    "/ws/schemas",
    response_model=WebSocketEventCatalog,
    operation_id="get_session_ws_schemas",
    summary="WebSocket event schema catalog",
    description=(
        "Reference endpoint used by frontend codegen to discover the "
        "discriminated unions exchanged over the session WebSocket. "
        "The runtime payload is empty — only the OpenAPI schema matters."
    ),
)
async def get_session_ws_schemas() -> WebSocketEventCatalog:
    return WebSocketEventCatalog()


@ws_router.websocket("/ws/{session_id}")
async def session_websocket(websocket: WebSocket, session_id: UUID) -> None:
    container: AsyncContainer = websocket.app.state.dishka_container

    try:
        user_id = await _authenticate(websocket, container)
    except _AuthFailed:
        return

    try:
        session = await _load_session(container, session_id=session_id, user_id=user_id)
    except SessionNotFoundError:
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Session not found",
        )
        return
    except SessionAccessDeniedError:
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Session access denied",
        )
        return

    await websocket.accept()
    await _send(
        websocket,
        SessionSnapshotEvent(session=to_session_snapshot_payload(session)),
    )

    handler = _SessionWebSocketHandler(
        websocket=websocket,
        container=container,
        session_id=session_id,
        user_id=user_id,
    )

    try:
        while True:
            raw = await websocket.receive_json()
            try:
                event = _CLIENT_EVENT_ADAPTER.validate_python(raw)
            except ValidationError as exc:
                await _send(
                    websocket,
                    ErrorEvent(
                        code="invalid_event",
                        message=f"Invalid client event: {exc.errors(include_url=False)}",
                    ),
                )
                continue

            await handler.dispatch(event)
    except WebSocketDisconnect:
        return
    except Exception:
        logger.exception("Unhandled error on session WebSocket %s", session_id)
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)


# --------------------------------------------------------------------- #
# Authentication & loading
# --------------------------------------------------------------------- #


class _AuthFailed(Exception):
    pass


async def _authenticate(
    websocket: WebSocket,
    container: AsyncContainer,
) -> UUID:
    auth_settings = AuthSettings()
    token = websocket.cookies.get(auth_settings.access_token_cookie_name)
    if not token:
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Authentication required",
        )
        raise _AuthFailed

    try:
        token_issuer = await container.get(TokenIssuer)
        payload = token_issuer.validate(token, expected_type=TokenType.ACCESS)
    except Exception:
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Invalid or expired token",
        )
        raise _AuthFailed from None

    return payload.user_id


async def _load_session(
    container: AsyncContainer,
    *,
    session_id: UUID,
    user_id: UUID,
) -> Session:
    async with container() as request_container:
        repository = await request_container.get(SessionRepository)
        session = await repository.get_by_id(session_id=session_id)
        session.has_access(user_id)
        return session


# --------------------------------------------------------------------- #
# Command dispatching
# --------------------------------------------------------------------- #


class _SessionWebSocketHandler:
    def __init__(
        self,
        *,
        websocket: WebSocket,
        container: AsyncContainer,
        session_id: UUID,
        user_id: UUID,
    ) -> None:
        self._websocket = websocket
        self._container = container
        self._session_id = session_id
        self._user_id = user_id

    async def dispatch(self, event: ClientEvent) -> None:
        try:
            await self._dispatch(event)
        except (
            EmptyFollowUpAnswerError,
            FollowUpOptionNotFoundError,
            FollowUpQuestionAlreadyResolvedError,
            FollowUpQuestionNotFoundError,
            NoPendingFollowUpGroupError,
            PendingFollowUpQuestionsError,
            PendingToolCallsError,
            PlaylistTrackNotFoundError,
        ) as exc:
            await _send(
                self._websocket,
                ErrorEvent(
                    code=type(exc).__name__,
                    message=str(exc) or type(exc).__name__,
                    correlation_id=getattr(event, "correlation_id", None),
                ),
            )
        except SessionAccessDeniedError as exc:
            await _send(
                self._websocket,
                ErrorEvent(
                    code="session_access_denied",
                    message=str(exc) or "Session access denied",
                    correlation_id=getattr(event, "correlation_id", None),
                ),
            )

    async def _dispatch(self, event: ClientEvent) -> None:
        if isinstance(event, SendMessageCommand):
            await self._handle_send_message(event)
        elif isinstance(event, AnswerFollowUpWithOptionCommand):
            await self._handle_answer_follow_up_option(event)
        elif isinstance(event, AnswerFollowUpWithTextCommand):
            await self._handle_answer_follow_up_text(event)
        elif isinstance(event, SkipFollowUpCommand):
            await self._handle_skip_follow_up(event)
        elif isinstance(event, AddPlaylistTrackCommand):
            await self._handle_add_track(event)
        elif isinstance(event, RemovePlaylistTrackCommand):
            await self._handle_remove_track(event)

    async def _handle_send_message(self, event: SendMessageCommand) -> None:
        async with self._container() as request_container:
            repository = await request_container.get(SessionRepository)
            session = await self._authorized_session(repository)
            message = session.add_user_message(content=event.content)
            await repository.create(session=session)

        await _send(
            self._websocket,
            UserMessageAppendedEvent(message=to_message_payload(message)),
        )

    async def _handle_answer_follow_up_option(
        self,
        event: AnswerFollowUpWithOptionCommand,
    ) -> None:
        async with self._container() as request_container:
            repository = await request_container.get(SessionRepository)
            session = await self._authorized_session(repository)
            question = session.answer_follow_up_with_option(
                question_id=event.question_id,
                option_id=event.option_id,
            )
            group = session._find_pending_follow_up_group()  # noqa: SLF001
            group_id = (
                group.id if group is not None else _last_follow_up_group_id(session)
            )
            await repository.create(session=session)

        await _send(
            self._websocket,
            FollowUpAnsweredEvent(
                group_id=group_id,
                question_id=question.id,
                answer_text=question.answer_text or "",
                answered_option_id=question.answered_option_id,
            ),
        )

    async def _handle_answer_follow_up_text(
        self,
        event: AnswerFollowUpWithTextCommand,
    ) -> None:
        async with self._container() as request_container:
            repository = await request_container.get(SessionRepository)
            session = await self._authorized_session(repository)
            question = session.answer_follow_up_with_text(
                question_id=event.question_id,
                text=event.text,
            )
            group = session._find_pending_follow_up_group()  # noqa: SLF001
            group_id = (
                group.id if group is not None else _last_follow_up_group_id(session)
            )
            await repository.create(session=session)

        await _send(
            self._websocket,
            FollowUpAnsweredEvent(
                group_id=group_id,
                question_id=question.id,
                answer_text=question.answer_text or "",
                answered_option_id=question.answered_option_id,
            ),
        )

    async def _handle_skip_follow_up(self, event: SkipFollowUpCommand) -> None:
        async with self._container() as request_container:
            repository = await request_container.get(SessionRepository)
            session = await self._authorized_session(repository)
            question = session.skip_follow_up(question_id=event.question_id)
            group = session._find_pending_follow_up_group()  # noqa: SLF001
            group_id = (
                group.id if group is not None else _last_follow_up_group_id(session)
            )
            await repository.create(session=session)

        await _send(
            self._websocket,
            FollowUpSkippedEvent(
                group_id=group_id,
                question_id=question.id,
            ),
        )

    async def _handle_add_track(self, event: AddPlaylistTrackCommand) -> None:
        async with self._container() as request_container:
            repository = await request_container.get(SessionRepository)
            session = await self._authorized_session(repository)
            playlist_existed_before = session.playlist is not None
            track = session.add_track(
                title=event.title,
                artist=event.artist,
                year=event.year,
                cover_url=event.cover_url,
            )
            await repository.create(session=session)
            playlist = session.playlist

        if playlist is None:
            return

        if not playlist_existed_before:
            await _send(
                self._websocket,
                PlaylistSetEvent(playlist=to_playlist_payload(playlist)),
            )
            return

        await _send(
            self._websocket,
            PlaylistTrackAddedEvent(
                playlist_id=playlist.id,
                track=to_playlist_track_payload(track),
            ),
        )

    async def _handle_remove_track(self, event: RemovePlaylistTrackCommand) -> None:
        async with self._container() as request_container:
            repository = await request_container.get(SessionRepository)
            session = await self._authorized_session(repository)
            playlist = session.playlist
            session.remove_track(track_id=event.track_id)
            await repository.create(session=session)

        if playlist is None:
            return

        await _send(
            self._websocket,
            PlaylistTrackRemovedEvent(
                playlist_id=playlist.id,
                track_id=event.track_id,
            ),
        )

    async def _authorized_session(self, repository: SessionRepository) -> Session:
        session = await repository.get_by_id(session_id=self._session_id)
        session.has_access(self._user_id)
        return session


def _last_follow_up_group_id(session: Session) -> UUID:
    for message in reversed(session.messages):
        if message.follow_up_group is not None:
            return message.follow_up_group.id
    raise NoPendingFollowUpGroupError(
        f"Session {session.id} has no follow-up question groups."
    )


# --------------------------------------------------------------------- #
# Transport helpers
# --------------------------------------------------------------------- #


async def _send(websocket: WebSocket, event: ServerEvent) -> None:
    if websocket.client_state != WebSocketState.CONNECTED:
        return
    await websocket.send_json(_SERVER_EVENT_ADAPTER.dump_python(event, mode="json"))
